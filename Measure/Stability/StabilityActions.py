from datetime import datetime
import logging
import time
from math import floor
from DBBand6Cart.schemas.DUT_Type import DUT_Type
from INSTR.SignalGenerator.Keysight_PSG_MXG import SignalGenerator
from INSTR.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from INSTR.Chopper.Interface import Chopper_Interface, ChopperState
from INSTR.PNA.AgilentPNA import DEFAULT_POWER_CONFIG, FAST_CONFIG
from Control.CartAssembly import CartAssembly
from Control.RFSource import RFSource
from Control.IFSystem.Interface import IFSystem_Interface, InputSelect, OutputSelect
from Control.PowerDetect.Interface import PowerDetect_Interface, DetectMode
from Control.IFAutoLevel import IFAutoLevel
from Control.RFAutoLevel import RFAutoLevel
from Measure.Shared.MeasurementStatus import MeasurementStatus
from Measure.Shared.DataDisplay import DataDisplay
from Measure.Shared.SelectPolarization import SelectPolarization
from Measure.Shared.SelectSideband import SelectSideband
from AmpPhaseDataLib.TimeSeriesAPI import TimeSeriesAPI, TimeSeries
from AmpPhasePlotLib.PlotAPI import PlotAPI
from AmpPhaseDataLib.Constants import Units, DataSource, SpecLines, DataKind, PlotEl, StabilityUnits
from ..Shared.Sampler import Sampler
from .CalcDataInterface import CalcDataInterface, StabilityRecord
from .SettingsContainer import SettingsContainer
from .schemas import Settings as StabilitySettings, StabilitySample
from DebugOptions import *

class StabilityActions():

    def __init__(self,
            loReference: SignalGenerator,
            receiver: CartAssembly,            
            ifSystem: IFSystem_Interface,
            tempMonitor: TemperatureMonitor,
            chopper: Chopper_Interface,
            rfSrcDevice: RFSource,              # for phase stability only            
            measurementStatus: MeasurementStatus,
            dataDisplay: DataDisplay,
            dutType: DUT_Type,
            settings: SettingsContainer
    ):
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.loReference = loReference
        self.receiver = receiver
        self.rfSrcDevice = rfSrcDevice        
        self.ifSystem = ifSystem
        self.powerDetect = None
        self.tempMonitor = tempMonitor
        self.chopper = chopper
        self.measurementStatus = measurementStatus
        self.dataDisplay = dataDisplay
        self.dutType = dutType
        self.settings = settings
        self.rfAutoLevel = RFAutoLevel(self.ifSystem, self.powerDetect, self.rfSrcDevice)
        self.timeSeriesAPI = None
        self.plotAPI = None
        self._reset()

    def setPowerDetect(self, powerDetect: PowerDetect_Interface) -> None:
        self.powerDetect = powerDetect
        self.rfAutoLevel = RFAutoLevel(self.ifSystem, self.powerDetect, self.rfSrcDevice)

    def _reset(self) -> None:
        self.finished = False
        self.dataDisplay.reset()

    def start(self, settings: StabilitySettings):
        self.measurementStatus.setStatusMessage("Started")
        self.measurementStatus.setComplete(False)
        self._reset()
        self.settings = settings
        if self.rfSrcDevice:
            self.rfSrcDevice.turnOff()

    def stop(self):        
        self.measurementStatus.setStatusMessage("Stopping...")
        self.measurementStatus.stopMeasuring()
        self.chopper.gotoHot()
        if self.rfSrcDevice:
            self.rfSrcDevice.turnOff()
        
    def finish(self):
        self.powerDetect.reset()
        self.settings = None
        self.measurementStatus.setComplete(True)
        self.measurementStatus.setMeasuring(None)
        self.measurementStatus.setStatusMessage("Finished")

    #### LO & IF STEPPING ####################################

    def setLO(self, freqLO: float, setBias: bool = True) -> tuple[bool, str]:
        
        self.measurementStatus.setStatusMessage(f"Locking LO at {freqLO:.2f} GHz...")
        success, msg = self.receiver.lockLO(self.loReference, freqLO)

        locked = success        
        if not success:
            self.logger.error(msg)
        elif msg:
            self.logger.info(msg)

        if setBias:
            success = self.receiver.setRecevierBias(freqLO)
            if not success:
                return False, "setRecevierBias failed. Provide config ID?"
            
            self.measurementStatus.setStatusMessage(f"Setting LO power...")
            selectPol = SelectPolarization(self.settings.polarization)
            success = self.receiver.autoLOPower(selectPol.testPol(0), selectPol.testPol(1))
            if not success:
                return False, "cartAssembly.autoLOPower failed"

        if locked:
            return True, f"Locked LO {'and set bias ' if setBias else ''}at {freqLO:.2f} GHz."
        else:
            return True, f"LO LOCK FAILED {'and set bias ' if setBias else ''}at {freqLO:.2f} GHz."

    def getLO(self) -> float:
        return self.receiver.freqLOGHz

    def setIF(self, freqIF: float = 0) -> tuple[bool, str]:
        self.ifSystem.frequency = freqIF
        return True, ""

    def getIF(self) -> float:
        return self.ifSystem.frequency
    
    #### RF SOURCE CONTROL ####################################

    def lockRF(self, freqRF: float) -> tuple[bool, str]:
        if not self.rfSrcDevice:
            raise ValueError("lockRF: no rfSrcDevice")
        self.measurementStatus.setStatusMessage(f"Locking RF at {freqRF} GHz...")
        self.rfSrcDevice.selectLockSideband(self.rfSrcDevice.LOCK_ABOVE_REF)
        wcaFreq, ytoFreq, ytoCourse = self.rfSrcDevice.setLOFrequency(freqRF)
        if not SIMULATE:
            wcaFreq, ytoFreq, ytoCourse = self.rfSrcDevice.lockPLL()
        return (wcaFreq != 0, f"lockRF: wca={wcaFreq}, yto={ytoFreq}, courseTune={ytoCourse}")      
    
    def rfSourceAutoLevel(self, freqIF: float) -> tuple[bool, str]:
        if not self.rfSrcDevice:
            raise ValueError("rfSourceAutoLevel: no rfSrcDevice")    
        self.measurementStatus.setStatusMessage("Adjusting RF level...")
        self.ifSystem.output_select = OutputSelect.PNA_INTERFACE    
        self.ifSystem.attenuation = self.settings.attenuateIF
        self.powerDetect.configure(power_config = DEFAULT_POWER_CONFIG, config = FAST_CONFIG)
        success = self.rfAutoLevel.autoLevel(freqIF, self.settings.targetLevel)
        if SIMULATE:
            success = True
        return (success, "rfSourceAutoLevel")
    
    #### MEASUREMENT HELPERS ##################################

    def delayAfterLock(self):
        success = True
        msg = ""
        
        timeStart = time.time()
        timeEnd = timeStart + self.settings.delayAfterLock * 60
        done = False
        while not done:
            now = time.time()
            if self.measurementStatus.stopNow():
                done = self.finished = True
                msg = "User stop"
            elif now >= timeEnd:
                done = True                
            else:
                self.receiver.loDevice.adjustPLL()
                elapsed = timeEnd - now 
                minutes = floor(elapsed / 60)
                seconds = elapsed - (minutes * 60)
                self.measurementStatus.setStatusMessage(f"Delay after lock: {minutes:02.0f}:{seconds:02.0f}")
                time.sleep(1)
        
        pll = self.receiver.loDevice.getLockInfo()
        if not pll['isLocked'] and not SIMULATE:
            success = False
            msg = "StabilityActions.delayAfterLock LO unlocked"
        return success, msg

    #### PHASE STABLILITY #####################################

    def measurePhase(self, 
            phaseSeries: TimeSeries,
            loCorrVSeries: TimeSeries | None = None,
            rfCorrVSeries: TimeSeries | None = None
        ) -> tuple[bool, str]:
        # create these here because SQLite connection must be created in same thread it is used:        
        self.timeSeriesAPI = TimeSeriesAPI()
        self.plotAPI = PlotAPI()

        self.powerDetect.configure(power_config = DEFAULT_POWER_CONFIG, config = FAST_CONFIG)

        temp = self.timeSeriesAPI.startTimeSeries(startTime = phaseSeries.startTime, dataUnits = phaseSeries.dataUnits)
        if not temp.tsId:
            return False, "measurePhase: TimeSeriesAPI.startTimeSeries error"
        phaseSeries.tsId = temp.tsId
        self.measurementStatus.setStatusMessage("Measuring...")
        self.measurementStatus.setChildKey(phaseSeries.tsId)
        self.dataDisplay.stabilityHistory = []     
        
        success = True
        msg = ""
        temperature = None
        phase = None

        # functions to give to the Samplers:
        def read_temperature():
            nonlocal temperature
            temperature, _ = self.tempMonitor.readSingle(self.settings.sensorAmbient)

        def read_phase_corrv():
            nonlocal temperature, phase, phaseSeries, loCorrVSeries, rfCorrVSeries
            _, phase = self.powerDetect.read(amp_phase = True)
            phaseSeries.appendData(
                phase,
                temperature, 
                timeStamps = datetime.now()
            )
            if loCorrVSeries is not None:
                pll = self.receiver.loDevice.getPLL()
                loCorrVSeries.appendData(
                    pll['corrV'],
                    pll['temperature'],
                    timeStamps = datetime.now()
                )
            if rfCorrVSeries is not None:
                pll = self.rfSrcDevice.getPLL()
                rfCorrVSeries.appendData(
                    pll['corrV'],
                    pll['temperature'],
                    timeStamps = datetime.now()
                )

        # read the temperature once at the start so no race condition between the Samplers:
        read_temperature()
        # start up a Sampler for temperature:
        temperatureSampler = Sampler(1, read_temperature)
        temperatureSampler.start(True)
        # start up a Sampler for phase:
        phaseSampler = Sampler(1 / self.settings.sampleRate, read_phase_corrv)
        timeStart = time.time()
        timeEnd = timeStart + self.settings.measureDuration * 60
        phaseSampler.start(True)

        done = False
        while not done:                
            if self.measurementStatus.stopNow():
                done = self.finished = True
                msg = "User stop"
            elif time.time() >= timeEnd:
                done = True
            elif phase is not None:
                self.dataDisplay.stabilityHistory.append(StabilitySample(
                    key = phaseSeries.tsId,
                    timeStamp = datetime.now(),
                    amp_or_phase = phase,
                    temperature = temperature                        
                ))
            time.sleep(1 / self.settings.sampleRate)

        # stop the samplers:
        timeEnd = time.time()
        phaseSampler.stop()
        temperatureSampler.stop()

        if not phaseSeries.isDirty():
            return False, "measurePhase: No data"
        
        # compute actual sampling interval:
        phaseSeries.timeStamps = []
        phaseSeries.tau0Seconds = (timeEnd - timeStart) / (len(phaseSeries.dataSeries) - 1)
        
        self.timeSeriesAPI.finishTimeSeries(phaseSeries)
        return success, msg

    #### AMPLITUDE STABILITY ##################################

    def measureAmplitude(self, ampSeries: TimeSeries) -> tuple[bool, str]:
        # create these here because SQLite connection must be created in same thread it is used:        
        self.timeSeriesAPI = TimeSeriesAPI()
        self.plotAPI = PlotAPI()

        self.powerDetect.configure()

        temp = self.timeSeriesAPI.startTimeSeries(startTime = ampSeries.startTime, dataUnits = ampSeries.dataUnits)
        if not temp.tsId:
            return False, "measureAmplitude: TimeSeriesAPI.startTimeSeries error"
        ampSeries.tsId = temp.tsId
        self.measurementStatus.setStatusMessage("Measuring...")
        self.measurementStatus.setChildKey(ampSeries.tsId)
        self.dataDisplay.stabilityHistory = []     
        
        success = True
        msg = ""
        temperature = None
        amplitude = None

        # functions to give to the Samplers:        
        def read_temperature():
            nonlocal temperature
            temperature, _ = self.tempMonitor.readSingle(self.settings.sensorAmbient)
        
        def read_meter():
            nonlocal temperature, amplitude
            amplitudes = self.powerDetect.read()
            amplitude = amplitudes[-1]
            ampSeries.appendData(
                amplitudes, 
                [temperature for i in range(len(amplitudes))], 
                timeStamps = [datetime.now() for i in range(len(amplitudes))]
            )

        # read the temperature once at the start so no race condition between the Samplers:
        read_temperature()
        # start up a Sampler for temperature:
        temperatureSampler = Sampler(1, read_temperature)
        temperatureSampler.start(True)
        # start up a Sampler for voltage:
        voltageSampler = Sampler(1 / self.settings.sampleRate, read_meter)
        timeStart = time.time()
        timeEnd = timeStart + self.settings.measureDuration * 60
        voltageSampler.start(True)

        done = False
        while not done:                
            if self.measurementStatus.stopNow():
                done = self.finished = True
                msg = "User stop"
            elif time.time() >= timeEnd:
                done = True
            elif amplitude is not None:
                self.dataDisplay.stabilityHistory.append(StabilitySample(
                    key = ampSeries.tsId,
                    timeStamp = datetime.now(),
                    amp_or_phase = amplitude,
                    temperature = temperature                        
                ))
            time.sleep(10 / self.settings.sampleRate)

        # stop the samplers:
        timeEnd = time.time()
        voltageSampler.stop()
        temperatureSampler.stop()

        if not ampSeries.isDirty():
            return False, "measureAmplitude: No data"

        # compute actual sampling interval:
        ampSeries.timeStamps = []
        ampSeries.tau0Seconds = (timeEnd - timeStart) / (len(ampSeries.dataSeries) - 1)
        
        self.timeSeriesAPI.finishTimeSeries(ampSeries)
        return success, msg

    #### PLOTTING #############################################

    def plotTimeSeries(self, 
            timeSeries: TimeSeries, 
            title: str = "Time series",
            tempSensorLegend: str = None,
            dataSources: dict[DataSource, str:int] = None
        ) -> bytes | None:
        self.measurementStatus.setStatusMessage(f"Plotting {title}...")
        plotEls = { 
            PlotEl.TITLE : title 
        }
        if tempSensorLegend:
            plotEls[PlotEl.Y2_LEGEND1] = tempSensorLegend
        unwrapPhase = timeSeries.dataUnits == Units.DEG
        if self.plotAPI.plotTimeSeries(timeSeries, dataSources, plotEls, unwrapPhase = unwrapPhase):
            return self.plotAPI.imageData
        else:
            return None

    def plotAmplitudeStability(self, 
            timeSeries: TimeSeries,
            title = "Amplitude stability"
        ) -> tuple[bytes | None, dict | None]:
        self.measurementStatus.setStatusMessage("Plotting amplitude stability...")
        plotEls = {
            PlotEl.TITLE : title,
            PlotEl.SPEC_LINE1 : SpecLines.BAND6_AMP_STABILITY1, 
            PlotEl.SPEC_LINE2 : SpecLines.BAND6_AMP_STABILITY2,
            PlotEl.Y_AXIS_LABEL : StabilityUnits.AVAR_TAU.value.format(round(timeSeries.tau0Seconds, 2))
        }
        if self.plotAPI.plotAmplitudeStability(timeSeries.tsId, None, plotEls):
            return self.plotAPI.imageData, self.plotAPI.getCalcTrace()
        else:
            return None, None
            
    def plotPhaseStability(self,
            timeSeries: TimeSeries,
            title = "Phase stability"
        ) -> tuple[bytes | None, dict | None]:
        self.measurementStatus.setStatusMessage("Plotting phase stability...")
        plotEls = {
            PlotEl.TITLE : title,
            PlotEl.SPEC_LINE1 : SpecLines.BAND6_PHASE_STABILITY1, 
            PlotEl.SPEC_LINE2 : SpecLines.BAND6_PHASE_STABILITY2,
            PlotEl.SPEC2_NAME : "CTS test limit",
            PlotEl.PHASE_FS : "0"
        }
        if self.plotAPI.plotPhaseStability(timeSeries.tsId, None, plotEls):
            return self.plotAPI.imageData, self.plotAPI.getCalcTrace()
        else:
            return None, None
            
    def plotSpectrum(self,
            timeSeries: TimeSeries,
            title = "Spectrum"
        ) -> bytes | None:
        self.measurementStatus.setStatusMessage("Plotting spectrum...")
        plotEls = {
            PlotEl.TITLE: title
        }
        if self.plotAPI.plotSpectrum(timeSeries, None, plotEls):
            return self.plotAPI.imageData
        else:
            return None

    def plotAmplitudeEnsemble(self,
            timeSeriesIds: list[int],
            title = "Amplitude stability",
            tau0Seconds: float = 0.05
        ) -> bytes | None:
        self.measurementStatus.setStatusMessage("Plotting amplitude stability...")
        plotEls = {
            PlotEl.TITLE : title,
            PlotEl.SPEC_LINE1 : SpecLines.BAND6_AMP_STABILITY1, 
            PlotEl.SPEC_LINE2 : SpecLines.BAND6_AMP_STABILITY2,
            PlotEl.Y_AXIS_LABEL : StabilityUnits.AVAR_TAU.value.format(round(tau0Seconds, 2))
        }
        if self.plotAPI.plotAmplitudeStability(timeSeriesIds, None, plotEls):
            return self.plotAPI.imageData
        else:
            return None

    def plotPhaseEnsemble(self,
            timeSeriesIds: list[int],
            title = "Phase stability"
        ) -> bytes | None:
        self.measurementStatus.setStatusMessage("Plotting phase stability...")
        plotEls = {
            PlotEl.TITLE : "Phase stability",
            PlotEl.SPEC_LINE1 : SpecLines.BAND6_PHASE_STABILITY1, 
            PlotEl.SPEC_LINE2 : SpecLines.BAND6_PHASE_STABILITY2,
            PlotEl.SPEC2_NAME : "CTS test limit",
            PlotEl.PHASE_FS : "0"
        }
        if self.plotAPI.plotPhaseStability(timeSeriesIds, None, plotEls):
            return self.plotAPI.imageData
        else:
            return None
    
