from CTSDevices.WarmIFPlate.WarmIFPlate import WarmIFPlate
from CTSDevices.WarmIFPlate.OutputSwitch import OutputSelect, LoadSelect, PadSelect
from CTSDevices.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from CTSDevices.SignalGenerator.Keysight_PSG_MXG import SignalGenerator
from CTSDevices.DMM.HP34401 import HP34401, Function, AutoZero
from CTSDevices.FEMC.CartAssembly import CartAssembly
from DBBand6Cart.CartTests import CartTest, CartTests
from DBBand6Cart.TestResults import DataStatus
from DBBand6Cart.AmplitudeStability import AmplitudeStability as AmplitudeStability_DB
from DBBand6Cart.schemas.AmplitudeStabilityRecord import AmplitudeStabilityRecord
from app.database.CTSDB import CTSDB
from AmpPhaseDataLib.TimeSeriesAPI import TimeSeriesAPI
from AmpPhaseDataLib.TimeSeries import TimeSeries
from AmpPhaseDataLib.Constants import Units, DataSource
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
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers = 1)
        self.settings = None
        self.__reset()    

    def __reset(self):
        self.cartTest = None
        self.stopNow = False
        self.finished = False
        self.dataSources = {}
        self.timeSeriesList = []
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

        return success, msg

    def __acquire(self, freqLO: float, pol: int, sideband: int) -> Tuple[bool, str]:
        timeSeriesAPI = TimeSeriesAPI()
        self.timeSeries = timeSeriesAPI.startTimeSeries(startTime = datetime.now(), dataUnits = Units.VOLTS)
        if not self.timeSeries.tsId:
            return False, "AmplitudeStability.__acquire: TimeSeriesAPI.startTimeSeries error"
        
        self.measurementStatus.setStatusMessage("Measuring...")
        self.measurementStatus.setChildKey(self.timeSeries.tsId)

        success = True
        msg = ""
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
            timeSeriesAPI.finishTimeSeries(self.timeSeries)
            timeSeriesAPI.setDataSource(self.timeSeries.tsId, DataSource.CONFIG_ID, self.cartTest.configId)
            for key in self.dataSources.keys():
                timeSeriesAPI.setDataSource(self.timeSeries.tsId, key, self.dataSources[key])
            self.timeSeriesList.append(
                TimeSeriesInfo(
                    key = self.timeSeries.tsId,
                    freqLO = freqLO,
                    pol = pol,
                    sideband = sideband,
                    timeStamp = datetime.now(),
                    dataStatus = DataStatus.MEASURED.name
                )
            )
            plotAPI = PlotAPI()
            result = plotAPI.calculateAmplitudeStability(self.timeSeries.tsId)
            
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
            self.timeSeries.reset()
        return success, msg
                            
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
