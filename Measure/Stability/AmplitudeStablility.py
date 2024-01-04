from ALMAFE.common.GitVersion import gitVersion, gitBranch
from CTSDevices.WarmIFPlate.WarmIFPlate import WarmIFPlate
from CTSDevices.WarmIFPlate.OutputSwitch import OutputSelect, LoadSelect, PadSelect
from CTSDevices.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from CTSDevices.SignalGenerator.Keysight_PSG_MXG import SignalGenerator
from CTSDevices.DMM.HP34401 import HP34401, Function, AutoZero
from CTSDevices.FEMC.CartAssembly import CartAssembly
from DBBand6Cart.CartTests import CartTest, CartTests
from DBBand6Cart.TestResults import DataStatus, TestResult, TestResults
from DBBand6Cart.TestResultPlots import TestResultPlot, TestResultPlots
from DBBand6Cart.AmplitudeStability import AmplitudeStability as AmplitudeStability_DB
from DBBand6Cart.schemas.AmplitudeStabilityRecord import AmplitudeStabilityRecord
from app.database.CTSDB import CTSDB
from AmpPhaseDataLib.TimeSeriesAPI import TimeSeriesAPI
from AmpPhaseDataLib.TimeSeries import TimeSeries
from AmpPhaseDataLib.Constants import Units, DataSource, SpecLines, DataKind, PlotEl
from AmpPhasePlotLib.PlotAPI import PlotAPI
from ..Shared.makeSteps import makeSteps
from ..Shared.MeasurementStatus import MeasurementStatus
from .schemas import TimeSeriesInfo

from DebugOptions import *

from typing import Any, Dict, Tuple
import concurrent.futures
import logging
import time
from datetime import datetime
from math import floor

class AmplitudeStability():

    def __init__(self,
            loReference: SignalGenerator,
            cartAssembly: CartAssembly,
            warmIFPlate: WarmIFPlate,
            voltMeter: HP34401,
            tempMonitor: TemperatureMonitor,
            measurementStatus: MeasurementStatus):
        
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.loReference = loReference
        self.cartAssembly = cartAssembly
        self.warmIFPlate = warmIFPlate
        self.voltMeter = voltMeter
        self.tempMonitor = tempMonitor
        self.measurementStatus = measurementStatus
        self.DB = AmplitudeStability_DB(driver = CTSDB())
        self.DB_TR = TestResults(driver = CTSDB())
        self.DB_TRPlot = TestResultPlots(driver = CTSDB())
        self.timeSeriesAPI = None   # these must be created in the worker thread because SQLite
        self.plotAPI = None         #        
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers = 1)
        self.settings = None
        branch = gitBranch()
        commit = gitVersion(branch = branch)
        self.swVersion = branch + ":" + commit[0:7]
        self.__reset()    

    def __reset(self):
        self.cartTest = None
        self.stopNow = False
        self.finished = False
        self.dataSources = {}
        self.timeSeriesList = []
        self.plotIds = []
        self.timeSeries = TimeSeries(startTime = datetime.now(), dataUnits = Units.VOLTS)

    def setDataSources(self, sources: Dict[DataSource, Any]):
        self.dataSources = sources

    def start(self, cartTest: CartTest) -> int:
        self.__reset()
        cartTestsDb = CartTests(driver = CTSDB())
        self.cartTest = cartTest
        if not SIMULATE:
            self.cartTest.key = cartTestsDb.create(cartTest)
        else:
            self.cartTest.key = 1

        self.dataSources[DataSource.CONFIG_ID] = cartTest.configId
        self.dataSources[DataSource.SERIALNUM] = self.cartAssembly.serialNum
        self.dataSources[DataSource.DATA_KIND] = DataKind.AMPLITUDE.value
        self.dataSources[DataSource.TEST_SYSTEM] = cartTest.testSysName
        self.dataSources[DataSource.UNITS] = Units.VOLTS_SQ.value
        self.dataSources[DataSource.T_UNITS] = Units.KELVIN.value
        self.dataSources[DataSource.OPERATOR] = cartTest.operator
        self.dataSources[DataSource.NOTES] = cartTest.description
        self.dataSources[DataSource.MEAS_SW_NAME] = "ALMAFE-CTS-Control"       
        self.dataSources[DataSource.MEAS_SW_VERSION] = self.swVersion
        
        self.stopNow = False
        self.finished = False
        self.futures = []
        self.measurementStatus.setStatusMessage("Started")
        self.measurementStatus.setError(False)
        self.futures.append(self.executor.submit(self.__run))
        return self.cartTest.key

    def stop(self):
        self.measurementStatus.setStatusMessage("Stopping...")
        self.stopNow = True

    def isMeasuring(self) -> bool:
        return not self.finished

    def __run(self) -> None:
        success = True
        msg = ""
        self.timeSeriesAPI = TimeSeriesAPI()    # these must be created in the worker thread because SQLite
        self.plotAPI = PlotAPI()                #
        self.measurementStatus.setComplete(all = False)
        self.voltMeter.configureMeasurement(Function.DC_VOLTAGE)
        self.voltMeter.configureAutoZero(AutoZero.OFF)
        self.voltMeter.configureAveraging(Function.DC_VOLTAGE, 1)
        self.warmIFPlate.attenuator.setValue(3)
        self.warmIFPlate.outputSwitch.setValue(OutputSelect.POWER_METER, LoadSelect.THROUGH, PadSelect.PAD_OUT)
        loSteps = makeSteps(self.settings.loStart, self.settings.loStop, self.settings.loStep)
        for freqLO in loSteps:
            if self.stopNow:
                self.finished = True
                self.measurementStatus.setStatusMessage("User stop")
                self.measurementStatus.setMeasuring(None)
                self.measurementStatus.setComplete(all = True)
                self.logger.info("User stop")
                return

            self.measurementStatus.setComplete(step = False)
            success, msg = self.__runOneLO(freqLO)
            self.measurementStatus.setComplete(step = True)

            if not success:
                self.measurementStatus.setError(True)
                self.measurementStatus.setStatusMessage(msg)
                self.logger.error(msg)
            else:
                self.logger.info(msg)
        
        # create ensemble plot:
        self.__plotEnsemble()
                
        # create or update the record in TestResults table:
        testResult = TestResult(
            fkCartTests = self.cartTest.key,
            dataStatus = DataStatus.PROCESSED,
            whenProcessed = datetime.now(),
            measurementSW = self.swVersion,
            description = self.cartTest.description,
            timeStamp = datetime.now(),
            plots = self.plotIds)
        
        testResult = self.DB_TR.createOrUpdate(testResult)
        
        # check that testResult succeeded:
        if not testResult:
            msg = 'Error saving TestResult record.'
            self.logger.error(msg)
            self.measurementStatus.setStatusMessage(msg)
        else:
            self.measurementStatus.setStatusMessage("Finished")
        self.measurementStatus.setMeasuring(None)
        self.measurementStatus.setComplete(all = True)
        self.finished = True

    def __runOneLO(self, freqLO: float) -> Tuple[bool, str]:
        success, msg = self.cartAssembly.lockLO(self.loReference, freqLO)
        if not success:
            return success, msg

        success = self.cartAssembly.setRecevierBias(freqLO)
        if not success:
            return False, "cartAssembly.setRecevierBias failed. Provide config ID?"
        
        success = self.cartAssembly.setAutoLOPower()
        if not success:
            return False, "cartAssembly.setAutoLOPower failed"

        success, msg = self.__delayAfterLock()
        if not success:
            return success, msg

        success = self.cartAssembly.setAutoLOPower()
        if not success:
            return False, "cartAssembly.setAutoLOPower failed"

        pols = []
        if self.settings.measurePol0:
            pols.append(0)
        if self.settings.measurePol1:
            pols.append(1)

        sidebands = []
        if self.settings.measureUSB:
            sidebands.append('USB')
        if self.settings.measureLSB:
            sidebands.append('LSB')

        for pol in pols:
            for sideband in sidebands:
                if self.stopNow:
                    self.finished = True
                    return True, "User stop"

                self.warmIFPlate.inputSwitch.setPolAndSideband(pol, sideband)
                success, msg = self.__acquire(freqLO, pol, sideband)
                if success:
                    success, msg = self.__plotOneLO(freqLO, pol, sideband)    

        return success, msg

    def __acquire(self, freqLO: float, pol: int, sideband: int) -> Tuple[bool, str]:        
        success = True
        msg = ""
        
        self.timeSeries = self.timeSeriesAPI.startTimeSeries(startTime = datetime.now(), dataUnits = Units.VOLTS)
        if not self.timeSeries.tsId:
            return False, "AmplitudeStability.__acquire: TimeSeriesAPI.startTimeSeries error"
        
        self.measurementStatus.setStatusMessage("Measuring...")
        self.measurementStatus.setChildKey(self.timeSeries.tsId)

        sampleInterval = 1 / self.settings.sampleRate

        timeStart = time.time()
        timeEnd = timeStart + self.settings.measureDuration * 60
        done = False
        temperatureError = None
        while not done:
            sampleStart = time.time()
            sampleEnd = sampleStart + sampleInterval
            temp, err = self.tempMonitor.readSingle(self.settings.sensorAmbient)
            if err != 0 and not temperatureError:
                temperatureError = err
            self.timeSeries.appendData(self.voltMeter.readSinglePoint(), temp, timeStamps = datetime.now())
            if self.stopNow:
                done = self.finished = True
                msg = "User stop"
            now = time.time()
            if now >= timeEnd:
                done = True
            elif now < sampleEnd:
                time.sleep(sampleEnd - now)

        if temperatureError:
            self.logger.error(f"AmplitudeStability.__acquire: temperature monitor returned {temperatureError}")

        if not self.timeSeries.isDirty():
            success = False
            msg = "AmplitudeStability.__acquire: No data"
        
        else:
            self.timeSeriesAPI.finishTimeSeries(self.timeSeries)
            self.timeSeriesList.append(
                TimeSeriesInfo(
                    key = self.timeSeries.tsId,
                    freqLO = freqLO,
                    pol = pol,
                    sideband = sideband,
                    timeStamp = datetime.now(),
                    dataStatus = DataStatus.PROCESSED.name
                )
            )
        return success, msg

    def __plotOneLO(self, freqLO: float, pol: int, sideband: str) -> Tuple[bool, str]:
        success = True
        msg = ""

        self.timeSeriesAPI.setDataSource(self.timeSeries.tsId, DataSource.LO_GHZ, freqLO)   
        self.timeSeriesAPI.setDataSource(self.timeSeries.tsId, DataSource.SUBSYSTEM, f"pol{pol} {sideband}")
        for key in self.dataSources.keys():
            self.timeSeriesAPI.setDataSource(self.timeSeries.tsId, key, self.dataSources[key])            

        plotEls = {
            PlotEl.TITLE : f"Amplitude stability",
            PlotEl.SPEC_LINE1 : SpecLines.BAND6_AMP_STABILITY1, 
            PlotEl.SPEC_LINE2 : SpecLines.BAND6_AMP_STABILITY2
        }        
        success = self.plotAPI.plotAmplitudeStability(self.timeSeries.tsId, plotEls)
        if not success:
            msg = "AmplitudeStability.__plotOneLO: Error plotting amplitude stability"
        else:
            result = self.plotAPI.getCalcTrace()            
            records = [AmplitudeStabilityRecord(
                fkCartTest = self.cartTest.key,
                fkRawData = self.timeSeries.tsId,
                freqLO = freqLO,
                pol = pol,
                sideband = 0 if sideband.lower() == 'lsb' else 1,
                time = x,
                allanVar = y,
                errorBar = e
            ) for x, y, e in zip(result['x'], result['y'], result['yError'])]
            self.DB.create(records)
                
            plotDescription = f"Amplitude stability CCA {self.cartAssembly.serialNum} LO={freqLO} pol{pol} {sideband}"
        
            plotId = self.DB_TRPlot.create(TestResultPlot(plotBinary = self.plotAPI.imageData, description = plotDescription))
            if plotId:
                self.plotIds.append(plotId)
            else:
                success = False
                msg = "AmplitudeStability.__plotOneLO: Error creating TestResultPlot record."

        self.timeSeries.reset()
        return success, msg
                            
    def __plotEnsemble(self):
        if len(self.timeSeriesList) > 1:            
            plotEls = {
                PlotEl.TITLE : "Amplitude stability",
                PlotEl.SPEC_LINE1 : SpecLines.BAND6_AMP_STABILITY1, 
                PlotEl.SPEC_LINE2 : SpecLines.BAND6_AMP_STABILITY2
            }        
            success = self.plotAPI.plotAmplitudeStability([ts.key for ts in self.timeSeriesList], plotEls)
            if not success:
                msg = "AmplitudeStability.__plotEnsemble: Error plotting amplitude stability ensemble"
            else:
                plotId = self.DB_TRPlot.create(TestResultPlot(plotBinary = self.plotAPI.imageData, description = f"Ensemble plot for {self.cartTest.key}"))
                if plotId:
                    self.plotIds.append(plotId)


    def __delayAfterLock(self):
        success = True
        msg = ""
        
        timeStart = time.time()
        timeEnd = timeStart + self.settings.delayAfterLock * 60
        done = False
        while not done:
            now = time.time()
            if self.stopNow:
                done = self.finished = True
                msg = "User stop"
            elif now >= timeEnd:
                done = True                
            else:
                self.cartAssembly.loDevice.adjustPLL()
                elapsed = timeEnd - now 
                minutes = floor(elapsed / 60)
                seconds = elapsed - (minutes * 60)
                self.measurementStatus.setStatusMessage(f"Delay after lock: {minutes:02.0f}:{seconds:02.0f}")
                time.sleep(1)
        
        pll = self.cartAssembly.loDevice.getLockInfo()
        if not pll['isLocked'] and not SIMULATE:
            success = False
            msg = "AmplitudeStability.__delayAfterLock LO unlocked"
        return success, msg

    def getTimeSeries(self, 
            first: int = 0, 
            last: int = -1, 
            targetLength: int = None,
            latestOnly: bool = False) -> TimeSeries:
        
        averaging = 1
        if targetLength:
            averaging = self.timeSeries.getRecommendedAveraging(targetLength)
        return self.timeSeries.select(first, last, averaging = averaging, latestOnly = latestOnly)
