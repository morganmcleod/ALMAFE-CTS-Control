from ALMAFE.common.GitVersion import gitVersion, gitBranch
from INSTR.WarmIFPlate.WarmIFPlate import WarmIFPlate
from INSTR.WarmIFPlate.OutputSwitch import OutputSelect, LoadSelect, PadSelect
from INSTR.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from INSTR.SignalGenerator.Keysight_PSG_MXG import SignalGenerator
from Control.CartAssembly import CartAssembly
from DBBand6Cart.CartTests import CartTest, CartTests
from DBBand6Cart.TestResults import DataStatus, TestResult, TestResults
from DBBand6Cart.TestResultPlots import TestResultPlot, TestResultPlots
from DBBand6Cart.schemas.TestType import TestTypeIds
from app.database.CTSDB import CTSDB
from AmpPhaseDataLib.TimeSeriesAPI import TimeSeriesAPI
from AmpPhaseDataLib.TimeSeries import TimeSeries
from AmpPhaseDataLib.Constants import Units, DataSource, SpecLines, DataKind, PlotEl
from AmpPhasePlotLib.PlotAPI import PlotAPI
from AMB.LODevice import LODevice
from ..Shared.makeSteps import makeSteps
from ..Shared.MeasurementStatus import MeasurementStatus
from .schemas import TimeSeriesInfo, Settings
from .SampleInterface import SampleInterface
from .CalcDataInterface import CalcDataInterface, StabilityRecord

from DebugOptions import *

from typing import Any, Dict, Tuple
from enum import Enum
import concurrent.futures
import logging
import time
from datetime import datetime
from math import floor
import yaml

class MeasureStability():

    AMP_STABILITY_SETTINGS_FILE = "Settings_AmpStability.yaml"
    PHASE_STABILITY_SETTINGS_FILE = "Settings_PhaseStability.yaml"    

    def __init__(self,
            mode: str,      # 'AMPLITUDE' or 'PHASE'
            loReference: SignalGenerator,
            cartAssembly: CartAssembly,            
            warmIFPlate: WarmIFPlate,
            sampler: SampleInterface,
            tempMonitor: TemperatureMonitor,
            rfSrcDevice: LODevice,              # for phase stability only            
            measurementStatus: MeasurementStatus,
            calcDataInterface: CalcDataInterface
        ):
        
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.mode = mode
        self.loReference = loReference
        self.cartAssembly = cartAssembly
        self.warmIFPlate = warmIFPlate
        self.sampler = sampler
        self.tempMonitor = tempMonitor
        self.rfSrcDevice = rfSrcDevice
        self.measurementStatus = measurementStatus
        self.DB = calcDataInterface
        self.DB_TR = TestResults(driver = CTSDB())
        self.DB_TRPlot = TestResultPlots(driver = CTSDB())
        self.timeSeriesAPI = None   # these must be created in the worker thread because SQLite
        self.plotAPI = None         #        
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers = 1)
        self.settings = None
        self.signalIF = 10          # only used for phase stability
        branch = gitBranch()
        commit = gitVersion(branch = branch)
        self.swVersion = branch + ":" + commit[0:7]
        self.loadSettings()
        self.__reset()

    def __reset(self):
        self.cartTest = None
        self.stopNow = False
        self.finished = False
        self.dataSources = {}
        self.timeSeriesList = []
        self.timeSeriesInfo = None
        self.plotIds = []
        self.testResult = None
        self.units = self.sampler.getUnits()
        startTime = datetime.now()
        self.timeSeries = TimeSeries(startTime = startTime, dataUnits = self.units[0])
        if self.units[1]:
            self.timeSeries2 = TimeSeries(startTime = startTime, dataUnits = self.units[1])
        else:
            self.timeSeries2 = None    

    def loadSettings(self):
        try:
            with open(self.STABILITY_SETTINGS_FILE, "r") as f:
                d = yaml.safe_load(f)
                self.settings = Settings.parse_obj(d)
        except:            
            self.settings = Settings()
            if self.mode == 'PHASE':
                self.settings.sampleRate = 5
                self.settings.attenuateIF = 22
            self.saveSettings()

    def saveSettings(self):
        if self.mode == 'AMPLITUDE':
            with open(self.AMP_STABILITY_SETTINGS_FILE, "w") as f:
                yaml.dump(self.settings.dict(), f)
        elif self.mode == 'PHASE':
            with open(self.PHASE_STABILITY_SETTINGS_FILE, "w") as f:
                yaml.dump(self.settings.dict(), f)

    def start(self, cartTest: CartTest) -> int:
        self.__reset()
        cartTestsDb = CartTests(driver = CTSDB())
        self.cartTest = cartTest
        if not SIMULATE:
            self.cartTest.key = cartTestsDb.create(cartTest)
        else:
            self.cartTest.key = 1

        self.dataSources[DataSource.DATA_SOURCE] = f"CTS2 test ID {self.cartTest.key}"
        self.dataSources[DataSource.CONFIG_ID] = cartTest.configId
        self.dataSources[DataSource.SERIALNUM] = self.cartAssembly.serialNum
        self.dataSources[DataSource.DATA_KIND] = self.sampler.getDataKind().value
        self.dataSources[DataSource.TEST_SYSTEM] = cartTest.testSysName
        self.dataSources[DataSource.UNITS] = self.units[0].value
        self.dataSources[DataSource.T_UNITS] = Units.KELVIN.value
        self.dataSources[DataSource.OPERATOR] = cartTest.operator
        self.dataSources[DataSource.NOTES] = cartTest.description
        self.dataSources[DataSource.MEAS_SW_NAME] = "ALMAFE-CTS-Control"       
        self.dataSources[DataSource.MEAS_SW_VERSION] = self.swVersion
        
        self.stopNow = False
        self.finished = False
        self.futures = []
        self.futures.append(self.executor.submit(self.__run))
        self.measurementStatus.setStatusMessage("Started")
        self.measurementStatus.setError(False)
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
        self.measurementStatus.setComplete(False)
        self.sampler.configure()
        self.warmIFPlate.attenuator.setValue(self.settings.attenuateIF)
        if self.cartTest.fkTestType == TestTypeIds.PHASE_STABILITY.value:
            self.warmIFPlate.outputSwitch.setValue(OutputSelect.SQUARE_LAW, LoadSelect.THROUGH, PadSelect.PAD_OUT)
            self.warmIFPlate.yigFilter.setFrequency(self.signalIF)
        else:
            self.warmIFPlate.outputSwitch.setValue(OutputSelect.POWER_METER, LoadSelect.THROUGH, PadSelect.PAD_OUT)

        success, msg = self.__updateTestResult()
        if not success:
            self.measurementStatus.setStatusMessage(msg)
                
        loSteps = makeSteps(self.settings.loStart, self.settings.loStop, self.settings.loStep)
        for freqLO in loSteps:
            if self.stopNow:
                self.finished = True
                self.measurementStatus.setStatusMessage("User stop")
                self.measurementStatus.setMeasuring(None)
                self.measurementStatus.setComplete(True)
                self.logger.info("User stop")
                return

            success, msg = self.__runOneLO(freqLO)        
            if not success:
                self.measurementStatus.setError(True)
                self.measurementStatus.setStatusMessage(msg)
                self.logger.error(msg)
            else:
                self.logger.info(msg)
        
        # create ensemble plot:
        success, msg = self.__plotEnsemble()
        if not success:
            self.measurementStatus.setStatusMessage(msg)
        else:
            success, msg = self.__updateTestResult(DataStatus.PROCESSED)
            if not success:
                self.measurementStatus.setStatusMessage(msg)
            else:
                self.measurementStatus.setStatusMessage("Finished")

        self.measurementStatus.setMeasuring(None)
        self.measurementStatus.setComplete(True)
        self.finished = True

    def __runOneLO(self, freqLO: float) -> Tuple[bool, str]:
        success, msg = self.__rfSourceOff()

        self.measurementStatus.setStatusMessage(f"Locking LO at {freqLO} GHz...")
        success, msg = self.cartAssembly.lockLO(self.loReference, freqLO)
        if not success:
            return success, msg

        success = self.cartAssembly.setRecevierBias(freqLO)
        if not success:
            return False, "cartAssembly.setRecevierBias failed. Provide config ID?"
        
        if self.cartTest.fkTestType == TestTypeIds.AMP_STABILITY.value:
            success, msg = self.__delayAfterLock()
            if not success:
                return success, msg

            success = self.cartAssembly.autoLOPower()
            if not success:
                return False, "cartAssembly.autoLOPower failed"

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
                success = True
                msg = ""
                freqRF = 0
                if self.stopNow:
                    self.finished = True
                    return True, "User stop"

                success, msg = self.__rfSourceOff()                
                self.warmIFPlate.inputSwitch.set_pol_sideband(pol, sideband)
                    
                if self.cartTest.fkTestType == TestTypeIds.PHASE_STABILITY.value:
                    success = self.cartAssembly.autoLOPower()
                    freqRF = freqLO - self.signalIF if sideband.lower() == 'lsb' else freqLO + self.signalIF
                    self.measurementStatus.setStatusMessage(f"Locking RF at {freqRF} GHz...")
                    
                    success, msg = self.__lockRF(freqRF)
                    if success:
                        self.measurementStatus.setStatusMessage("Adjusting RF level...")
                        
                        success, msg = self.__rfSourceAutoLevel()
                        if success:
                            self.__delayAfterLock()
                
                if success:
                    success, msg = self.__acquire(freqLO, freqRF, pol, sideband)
                    if success:
                        success, msg = self.__plotOneLO(freqLO, freqRF, pol, sideband)
                        if success:
                            success, msg = self.__updateTestResult()

        return success, msg

    def __acquire(self, freqLO: float, freqRF: float, pol: int, sideband: int) -> Tuple[bool, str]:        
        success = True
        msg = ""
        
        self.timeSeries = self.timeSeriesAPI.startTimeSeries(startTime = datetime.now(), dataUnits = self.units[0])
        if not self.timeSeries.tsId:
            return False, "MeasureStability.__acquire: TimeSeriesAPI.startTimeSeries error"
        
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
            sample = self.sampler.getSample()
            timeStamp = datetime.now()
            self.timeSeries.appendData(sample[0], temp, timeStamps = timeStamp)
            if sample[1]:
                self.timeSeries2.appendData(sample[1], temp, timeStamps = timeStamp)                
            if self.stopNow:
                done = self.finished = True
                msg = "User stop"
            now = time.time()
            if now >= timeEnd:
                done = True
            elif now < sampleEnd:
                time.sleep(sampleEnd - now)

        if temperatureError:
            self.logger.error(f"MeasureStability.__acquire: temperature monitor returned {temperatureError}")

        if not self.timeSeries.isDirty():
            success = False
            msg = "MeasureStability.__acquire: No data"
        
        else:
            self.timeSeriesAPI.finishTimeSeries(self.timeSeries)
            self.timeSeriesInfo = TimeSeriesInfo(
                key = self.timeSeries.tsId,
                freqLO = freqLO,
                pol = pol,
                sideband = sideband,
                timeStamp = datetime.now(),
                dataStatus = DataStatus.PROCESSED.name
            )
            self.timeSeriesList.append(self.timeSeriesInfo)
        return success, msg

    def __plotOneLO(self, freqLO: float, freqRF: float, pol: int, sideband: str) -> Tuple[bool, str]:
        success = True
        msg = ""
        self.measurementStatus.setStatusMessage("Plotting...")

        self.timeSeriesAPI.setDataSource(self.timeSeries.tsId, DataSource.LO_GHZ, freqLO)
        self.timeSeriesAPI.setDataSource(self.timeSeries.tsId, DataSource.SUBSYSTEM, f"pol{pol} {sideband}")
        for key in self.dataSources.keys():
            self.timeSeriesAPI.setDataSource(self.timeSeries.tsId, key, self.dataSources[key])            

        plotEls = { PlotEl.TITLE : f"Time series" }
        unwrapPhase = self.cartTest.fkTestType == TestTypeIds.PHASE_STABILITY.value
        if self.plotAPI.plotTimeSeries(self.timeSeries.tsId, None, plotEls, unwrapPhase = unwrapPhase):
            plotDescription = f"Time series LO={freqLO} Pol{pol} {sideband}"
            plotId = self.DB_TRPlot.create(TestResultPlot(plotBinary = self.plotAPI.imageData, description = plotDescription))
            if plotId:
                self.plotIds.append(plotId)
                self.timeSeriesInfo.timeSeriesPlot = plotId
            else:
                self.logger.error("MeasureStability.__plotOneLO: Error plotting time series.")

        if self.cartTest.fkTestType == TestTypeIds.AMP_STABILITY.value:
            plotDescription = f"Amplitude stability LO={freqLO} Pol{pol} {sideband}"
            plotEls = {
                PlotEl.TITLE : "Amplitude stability",
                PlotEl.SPEC_LINE1 : SpecLines.BAND6_AMP_STABILITY1, 
                PlotEl.SPEC_LINE2 : SpecLines.BAND6_AMP_STABILITY2
            }
            success = self.plotAPI.plotAmplitudeStability(self.timeSeries.tsId, None, plotEls)
        
        elif self.cartTest.fkTestType == TestTypeIds.PHASE_STABILITY.value:
            plotDescription = f"Phase stability LO={freqLO} Pol{pol} {sideband}"
            plotEls = {
                PlotEl.TITLE : "Phase stability",
                PlotEl.SPEC_LINE1 : SpecLines.BAND6_PHASE_STABILITY1, 
                PlotEl.SPEC_LINE2 : SpecLines.BAND6_PHASE_STABILITY2,
                PlotEl.SPEC2_NAME : "CTS test limit"
            }
            success = self.plotAPI.plotPhaseStability(self.timeSeries.tsId, None, plotEls)
        
        else:
            raise ValueError(f"Unsupported fkTestType: {self.cartTest.fkTestType}")
        
        if not success:
            msg = "MeasureStability.__plotOneLO: Error plotting stability"
        else:
            result = self.plotAPI.getCalcTrace()            
            records = [StabilityRecord(
                fkCartTest = self.cartTest.key,
                fkRawData = self.timeSeries.tsId,
                timeStamp = datetime.now(),
                freqLO = freqLO,
                freqCarrier = freqRF,
                pol = pol,
                sideband = 0 if sideband.lower() == 'lsb' else 1,
                time = x,
                allan = y,
                errorBar = e
            ) for x, y, e in zip(result['x'], result['y'], result['yError'])]
            self.DB.create(records)
        
            plotId = self.DB_TRPlot.create(TestResultPlot(plotBinary = self.plotAPI.imageData, description = plotDescription))
            if plotId:
                self.plotIds.append(plotId)
                self.timeSeriesInfo.allanPlot = plotId
            else:
                success = False
                msg = "MeasureStability.__plotOneLO: Error creating TestResultPlot record."

        self.timeSeries.reset()
        if self.timeSeries2:
            self.timeSeries2.reset()
        return success, msg
                            
    def __plotEnsemble(self):
        success = True
        msg = ""
        self.measurementStatus.setStatusMessage("Plotting...")
                
        if len(self.timeSeriesList) > 1:            
            if self.cartTest.fkTestType == TestTypeIds.AMP_STABILITY.value:
                plotEls = {
                    PlotEl.TITLE : "Amplitude stability",
                    PlotEl.SPEC_LINE1 : SpecLines.BAND6_AMP_STABILITY1, 
                    PlotEl.SPEC_LINE2 : SpecLines.BAND6_AMP_STABILITY2
                }      
                success = self.plotAPI.plotAmplitudeStability([ts.key for ts in self.timeSeriesList], None, plotEls)
            elif self.cartTest.fkTestType == TestTypeIds.PHASE_STABILITY.value:
                plotEls = {
                    PlotEl.TITLE : "Phase stability",
                    PlotEl.SPEC_LINE1 : SpecLines.BAND6_PHASE_STABILITY1, 
                    PlotEl.SPEC_LINE2 : SpecLines.BAND6_PHASE_STABILITY2,
                    PlotEl.SPEC2_NAME : "CTS test limit"
                }
                success = self.plotAPI.plotPhaseStability([ts.key for ts in self.timeSeriesList], None, plotEls)
        
            else:
                raise ValueError(f"Unsupported fkTestType: {self.cartTest.fkTestType}")

            if not success:
                msg = "MeasureStability.__plotEnsemble: Error plotting amplitude stability ensemble"
            else:
                plotId = self.DB_TRPlot.create(TestResultPlot(plotBinary = self.plotAPI.imageData, description = f"Ensemble plot for {self.cartTest.key}"))
                if plotId:
                    self.plotIds.append(plotId)
        return success, msg

    def __updateTestResult(self, dataStatus = DataStatus.MEASURED) -> Tuple[bool, str]:
        # create or update the record in TestResults table:
        if not self.testResult:
            self.testResult = TestResult(
                fkCartTests = self.cartTest.key,
                dataStatus = dataStatus,
                measurementSW = self.swVersion,
                description = self.cartTest.description
            )
        
        self.testResult.plots = self.plotIds
        self.testResult.timeStamp = datetime.now()
        self.testResult = self.DB_TR.createOrUpdate(self.testResult)
        if not self.testResult:
            msg = 'Error saving TestResult record.'
            self.logger.error(msg)
            return False, msg
        else:
            return True, ""

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
            msg = "MeasureStability.__delayAfterLock LO unlocked"
        return success, msg
    
    def __rfSourceOff(self) -> Tuple[bool, str]:
        if self.rfSrcDevice:
            self.rfSrcDevice.setPAOutput(pol = self.rfSrcDevice.paPol, percent = 0)
        return (True, "")

    def __lockRF(self, freqRF: float) -> Tuple[bool, str]:
        if not self.rfSrcDevice:
            raise ValueError("__lockRF: no rfSrcDevice")
        self.rfSrcDevice.selectLockSideband(self.rfSrcDevice.LOCK_ABOVE_REF)
        wcaFreq, ytoFreq, ytoCourse = self.rfSrcDevice.setLOFrequency(freqRF)
        if not SIMULATE:
            wcaFreq, ytoFreq, ytoCourse = self.rfSrcDevice.lockPLL()
        return (wcaFreq != 0, f"__lockRF: wca={wcaFreq}, yto={ytoFreq}, courseTune={ytoCourse}")        
    
    def __rfSourceAutoLevel(self) -> Tuple[bool, str]:    
        if not self.rfSrcDevice:
            raise ValueError("__rfSourceAutoLevel: no rfSrcDevice")    
        success = self.rfSrcDevice.autoRFPower(self.sampler.pna, target = self.settings.targetLevel)
        return (success, "__rfSourceAutoLevel")

    def getTimeSeries(self, 
            first: int = 0, 
            last: int = -1, 
            targetLength: int = None,
            latestOnly: bool = False) -> TimeSeries:
        
        averaging = 1
        if targetLength:
            averaging = self.timeSeries.getRecommendedAveraging(targetLength)
        return self.timeSeries.select(first, last, averaging = averaging, latestOnly = latestOnly)
