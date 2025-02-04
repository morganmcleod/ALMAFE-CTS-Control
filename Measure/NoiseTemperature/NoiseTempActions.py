import time
from datetime import datetime
import logging
from statistics import mean, stdev
from math import sqrt, log10
from INSTR.SignalGenerator.Keysight_PSG_MXG import SignalGenerator
from INSTR.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from INSTR.PowerSupply.AgilentE363xA import PowerSupply
from INSTR.Chopper.Interface import Chopper_Interface, ChopperState
from INSTR.ColdLoad.AMI1720 import AMI1720
from Control.CartAssembly import CartAssembly
from Control.RFSource import RFSource
from Control.IFSystem.Interface import IFSystem_Interface, InputSelect, OutputSelect
from Control.PowerDetect.Interface import PowerDetect_Interface, DetectMode
from Control.IFAutoLevel import IFAutoLevel
from Control.RFAutoLevel import RFAutoLevel
from Measure.Shared.MeasurementStatus import MeasurementStatus
from Measure.Shared.DataDisplay import DataDisplay
from Measure.Shared.makeSteps import makeSteps
from Measure.Shared.SelectPolarization import SelectPolarization
from Measure.Shared.Sampler import Sampler
from Measure.NoiseTemperature.SettingsContainer import SettingsContainer
from .schemas import CommonSettings, WarmIFSettings, NoiseTempSettings, YFactorSettings, ChopperPowers, \
    SpecAnPowers, YFactorSample, BiasOptSettings, YFactorPowers
from DBBand6Cart.schemas.WarmIFNoise import WarmIFNoise
from DBBand6Cart.schemas.NoiseTempRawDatum import NoiseTempRawDatum
from DBBand6Cart.schemas.DUT_Type import DUT_Type

class NoiseTempActions():

    def __init__(self,
            loReference: SignalGenerator,
            rfReference: SignalGenerator,
            receiver: CartAssembly,
            rfSrcDevice: RFSource,
            ifSystem: IFSystem_Interface,
            powerDetect: PowerDetect_Interface,
            tempMonitor: TemperatureMonitor,
            powerSupply: PowerSupply,
            coldLoadController: AMI1720,
            chopper: Chopper_Interface,
            measurementStatus: MeasurementStatus,
            dataDisplay: DataDisplay,
            dutType: DUT_Type,
            settings: SettingsContainer):
    
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.loReference = loReference
        self.rfReference = rfReference
        self.receiver = receiver
        self.rfSrcDevice = rfSrcDevice        
        self.ifSystem = ifSystem
        self.powerDetect = powerDetect
        self.tempMonitor = tempMonitor
        self.powerSupply = powerSupply
        self.coldLoadController = coldLoadController
        self.chopper = chopper
        self.measurementStatus = measurementStatus
        self.dataDisplay = dataDisplay
        self.dutType = dutType
        self.settings = settings
        self.ifAutoLevel = IFAutoLevel(self.ifSystem, self.powerDetect, self.chopper)
        self.rfAutoLevel = RFAutoLevel(self.ifSystem, self.powerDetect, self.rfSrcDevice)
        self._reset()

    def _reset(self) -> None:
        self.finished = False
        self.dataDisplay.reset()

    def start(self, noiseTempSettings: NoiseTempSettings):
        self.noiseTempSettings = noiseTempSettings
        self.measurementStatus.setComplete(False)
        self.measurementStatus.setStatusMessage("Started")

    def stop(self):        
        self.measurementStatus.stopMeasuring()
        self.chopper.stop()
        self.rfSrcDevice.turnOff()

    def finish(self):
        self.noiseTempSettings = None
        self.measurementStatus.setComplete(True)
        self.measurementStatus.setMeasuring(None)
        self.measurementStatus.setStatusMessage("Finished")
        self.powerDetect.reset()
        
    def checkColdLoad(self) -> tuple[bool, str]:
        shouldPause, msg = self.coldLoadController.shouldPause(enablePause = self.settings.commonSettings.pauseForColdLoad)
        while shouldPause and not self.measurementStatus.stopNow():
            self.measurementStatus.setStatusMessage("Cold load " + msg)
            time.sleep(10)
            shouldPause, msg = self.coldLoadController.shouldPause(enablePause = self.settings.commonSettings.pauseForColdLoad)
        
        if self.measurementStatus.stopNow():
            self.finished = True                
            return True, "User stop"

        return True, msg

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
            selectPol = SelectPolarization(self.noiseTempSettings.polarization)
            success = self.receiver.autoLOPower(selectPol.testPol(0), selectPol.testPol(1))
            if not success:
                return False, "cartAssembly.autoLOPower failed"

        if locked:
            return True, f"Locked LO {'and set bias ' if setBias else ''}at {freqLO:.2f} GHz."
        else:
            return True, f"LO LOCK FAILED {'and set bias ' if setBias else ''}at {freqLO:.2f} GHz."

    def getLO(self) -> float:
        return self.receiver.freqLOGHz

    def setIF(self, freqIF: float = 0, ifAutoLevel: bool = True) -> tuple[bool, str]:

        self.ifSystem.frequency = freqIF

        success, msg = (True, "")
        if ifAutoLevel:
            success, msg = self.ifAutoLevel.autoLevel(self.settings.commonSettings.targetPHot)
        
        if not success:
            self.logger.error(msg)
        elif msg:
            self.logger.info(msg)
        return success, msg

    def getIF(self) -> float:
        return self.ifSystem.frequency

#### ZERO POWER METER #####################################

    def zeroPowerMeter(self) -> tuple[bool, str]:
        self._reset()
        if self.powerDetect.detect_mode != DetectMode.METER:
            return True, "zeroPowerMeter: nothing to do"

        self.powerDetect.configure(units = 'dBm', fast_mode = False)
        self.ifSystem.output_select = OutputSelect.LOAD
        self.powerDetect.zero()
        self.ifSystem.output_select = OutputSelect.POWER_DETECT
        self.measurementStatus.setStatusMessage("Zero Power Meter finished")
        self.measurementStatus.setComplete(True)

#### WARM IF SYSTEM NOISE #################################

    def measureIFSysNoise(self, 
            fkCartTest: int, 
            warmIFSettings: WarmIFSettings) -> list[WarmIFNoise]:
        self._reset()
        self.powerSupply.setOutputEnable(False)
        self.powerSupply.setVoltage(warmIFSettings.diodeVoltage)
        self.powerSupply.setCurrentLimit(warmIFSettings.diodeCurrentLimit)
        self.ifSystem.output_select = OutputSelect.POWER_DETECT
        self.ifSystem.input_select = InputSelect.NOISE_SOURCE
            
        attenSteps = makeSteps(warmIFSettings.attenStart, warmIFSettings.attenStop, warmIFSettings.attenStep)
        ifSteps = makeSteps(warmIFSettings.ifStart, warmIFSettings.ifStop, warmIFSettings.ifStep)

        records = []

        if self.powerDetect.detect_mode == DetectMode.METER:
            ### Warm IF Plate and power meter ###
            self.powerDetect.configure(units = 'W')
        
            for freq in ifSteps:
                self.ifSystem.frequency = freq
                for atten in attenSteps:
                    self.measurementStatus.setStatusMessage(f"Measuring IF System Noise: IF={freq:.2f} GHz, atten={atten} dB")
                    self.ifSystem.attenuation = atten
        
                    if self.measurementStatus.stopNow():
                        self.measurementStatus.setStatusMessage("User stop")
                        self.measurementStatus.setComplete(True)
                        self.finished = True
                        return records

                    self.powerSupply.setOutputEnable(True)
                    time.sleep(0.25)
                    pHot = self.powerDetect.read(mode = 'auto')
                    self.powerSupply.setOutputEnable(False)
                    time.sleep(0.25)
                    pCold = self.powerDetect.read(mode = 'auto')
                    ambient, err = self.tempMonitor.readSingle(self.settings.commonSettings.sensorAmbient)
                    record = WarmIFNoise(
                        fkCartTest = fkCartTest,
                        fkDUT_Type = self.dutType,
                        freqYig = freq,
                        atten = atten,
                        pHot = pHot,
                        pCold = pCold,
                        tAmbient = ambient,
                        noiseDiodeENR = warmIFSettings.diodeEnr
                    )
                    records.append(record)
        
        elif self.powerDetect.detect_mode == DetectMode.SPEC_AN:
            ### External switch and spectrum analyzer ###
            self.measurementStatus.setStatusMessage("Measuring IF System Noise")
            self.settings.ntSpecAnSettings.sweepPoints = int((warmIFSettings.ifStop - warmIFSettings.ifStart) / warmIFSettings.ifStep) + 1                
            self.powerDetect.configure(config = self.settings.ntSpecAnSettings, startGHz = warmIFSettings.ifStart, stopGHz = warmIFSettings.ifStop)

            self.powerSupply.setOutputEnable(True)
            time.sleep(0.25)
            x, pHots = self.powerDetect.read()
            self.powerSupply.setOutputEnable(False)
            time.sleep(0.25)
            x, pColds = self.powerDetect.read()

            ambient, err = self.tempMonitor.readSingle(self.settings.commonSettings.sensorAmbient)

            for freq, pHot, pCold in zip(x, pHots, pColds):
                records.append(
                    WarmIFNoise(
                        fkCartTest = fkCartTest,
                        fkDUT_Type = self.dutType,
                        freqYig = freq / 1e9,
                        atten = 0,
                        pHot = 10 ** (pHot / 10) / 1000,
                        pCold = 10 ** (pCold / 10) / 1000,
                        tIFCold = 0,
                        tIFHot = 0,
                        tAmbient = ambient,
                        noiseDiodeENR = warmIFSettings.diodeEnr
                    )   
                )                

        self.measurementStatus.setStatusMessage("Warm IF Noise: Done.")
        self.dataDisplay.warmIfData = records
        return records
    
#### Y-FACTOR #####################################################

    def measureYFactor(self, yFactorSettings: YFactorSettings) -> None:

        self.dataDisplay.yFactorHistory = []
        self.dataDisplay.yFactorPowers = []

        if self.powerDetect.detect_mode == DetectMode.METER or yFactorSettings.detectMode == DetectMode.METER:
            return self._measureYFactor_SINGLE(yFactorSettings)
        elif self.powerDetect.detect_mode == DetectMode.SPEC_AN or yFactorSettings.detectMode == DetectMode.SPEC_AN:
            return self._measureYFactor_SWEEP(yFactorSettings)
        else:
            return None
        
    def _measureYFactor_SINGLE(self, yFactorSettings: YFactorSettings) -> None:

        self.measurementStatus.setStatusMessage("Y-factor started")
        self.measurementStatus.setComplete(False)
        self.chopper.spin(self.settings.commonSettings.chopperSpeed)
        self.powerDetect.configure(units = 'dBm', fast_mode = False)
        self.ifSystem.output_select = OutputSelect.POWER_DETECT
        self.ifSystem.input_select = yFactorSettings.inputSelect

        chopperPowers = []

        def read():
            state = self.chopper.getState()
            power = self.powerDetect.read()
            chopperPowers.append(
                ChopperPowers(
                    inputName = self.ifSystem.input_select.name, 
                    chopperState = state, 
                    power = power
                )
            )

        sampling_interval = 1 / self.settings.commonSettings.sampleRate
        calculate_countdown = self.settings.commonSettings.powerMeterConfig.minS
        retain_samples = calculate_countdown * 2
        sampler = Sampler(sampling_interval, read)
        sampler.start()

        done = False
        while not done:
            if self.measurementStatus.stopNow():
                done = True
            else:
                calculate_countdown -= 1
                if calculate_countdown == 0:
                    self._calculateYFactor(chopperPowers, retain_samples)
                    calculate_countdown = self.settings.commonSettings.powerMeterConfig.minS
                if len(chopperPowers) > retain_samples:
                    chopperPowers = chopperPowers[-retain_samples:]
                time.sleep(sampling_interval)
        
        sampler.stop()
        self.chopper.stop()
        self.chopper.gotoHot()
        self.powerDetect.configure(fast_mode = False)
        self.measurementStatus.setStatusMessage("Y-factor stopped")
        self.measurementStatus.setComplete(True)
        self.finished = True

    def _measureYFactor_SWEEP(self, yFactorSettings: YFactorSettings) -> None:
        self.measurementStatus.setStatusMessage("Y-factor started")
        self.measurementStatus.setComplete(False)
        self.ifSystem.output_select = OutputSelect.POWER_DETECT
        self.ifSystem.input_select = yFactorSettings.inputSelect
        self.chopper.stop()
        self.chopper.gotoCold()
        
        if yFactorSettings.ifStart == yFactorSettings.ifStop:
            sweepPoints = 1
        else:
            sweepPoints = self.settings.ntSpecAnSettings.sweepPoints
        
        self.powerDetect.configure(
            config = self.settings.ntSpecAnSettings, 
            startGHz = yFactorSettings.ifStart, 
            stopGHz = yFactorSettings.ifStop,
            sweepPoints = sweepPoints)
        
        retain_samples = 20
        chopperPowers = []

        def read():
            self.chopper.gotoHot()
            chopperPowers.append(
                ChopperPowers(
                    inputName = self.ifSystem.input_select.name, 
                    chopperState = ChopperState.OPEN, 
                    power = self.powerDetect.read()
                )
            )
            self.chopper.gotoCold()
            chopperPowers.append(
                ChopperPowers(
                    inputName = self.ifSystem.input_select.name, 
                    chopperState = ChopperState.CLOSED, 
                    power = self.powerDetect.read()
                )
            )

        timeStart = time.time()
        read()
        sampling_interval = (time.time() - timeStart) * 1.2

        sampler = Sampler(sampling_interval, read)
        sampler.start()

        done = False
        while not done:
            if self.measurementStatus.stopNow():
                done = True
            else:
                self._calculateYFactor(chopperPowers, retain_samples)                
                if len(chopperPowers) > retain_samples:
                    chopperPowers = chopperPowers[-retain_samples:]
                time.sleep(sampling_interval)
        
        sampler.stop()
        self.chopper.stop()
        self.chopper.gotoHot()
        self.measurementStatus.setStatusMessage("Y-factor stopped")
        self.measurementStatus.setComplete(True)
        self.finished = True

    def _calculateYFactor(self, chopperPowers: list[ChopperPowers], retainSamples: int):
        N = self.settings.commonSettings.powerMeterConfig.minS * 3
        if N > len(chopperPowers):
            N = len(chopperPowers)

        pHot = [x.power for x in chopperPowers[-N:] if x.chopperState == ChopperState.OPEN]
        pCold = [x.power for x in chopperPowers[-N:] if x.chopperState == ChopperState.CLOSED]
        if not self.chopper.openIsHot:
            pHot, pCold = pCold, pHot

        if len(pHot) < 2 or len(pCold) < 2:
            return

        Y = mean(pHot) - mean(pCold)
        Ylinear = 10 ** (Y / 10)
        tAmb, tErr = self.tempMonitor.readSingle(self.settings.commonSettings.sensorAmbient)
        if tErr or tAmb < 1:
            return
        TRx = (tAmb - self.settings.commonSettings.tColdEff * Ylinear) / (Ylinear - 1)
        self.dataDisplay.yFactorHistory.append(YFactorSample(Y = Y, TRx = TRx))
        if len(self.dataDisplay.yFactorHistory) > retainSamples:
            self.dataDisplay.yFactorHistory = self.dataDisplay.yFactorHistory[-retainSamples:]
        self.dataDisplay.yFactorPowers += [
            YFactorPowers(
                inputName = self.ifSystem.input_select.name,
                pHot = h,
                pCold = c
            ) for h, c in zip(pHot, pCold)
        ]

#### NOISE TEMPERATURE #####################################
    
    def measureNoiseTemp(self,
            fkCartTest: int,
            freqLO: float,
            loIsLocked: bool,
            freqIF: float,
            recordsIn: dict[tuple[int, float], NoiseTempRawDatum] | None = None
            ) -> dict[tuple[int, float], NoiseTempRawDatum] | None:
        self.rfSrcDevice.turnOff()
        self.ifSystem.output_select = OutputSelect.POWER_DETECT
        self.ifSystem.input_select = InputSelect.POL0_USB
        selectPol = SelectPolarization(self.noiseTempSettings.polarization)

        if self.powerDetect.detect_mode == DetectMode.METER:
            
            if recordsIn is not None:
                records = recordsIn
            else:
                records = {}
            self._measureNoiseTemp_SINGLE(fkCartTest, freqLO, loIsLocked, freqIF, selectPol, records)
            return records
        
        elif self.powerDetect.detect_mode == DetectMode.SPEC_AN:
            ifSteps = makeSteps(self.noiseTempSettings.ifStart, self.noiseTempSettings.ifStop, self.noiseTempSettings.ifStep)
            if recordsIn is not None:
                records = recordsIn
            else:
                records = self._initRawData(fkCartTest, freqLO, loIsLocked, selectPol, ifSteps)
            self._measureNoiseTemp_SWEEP(freqLO, ifSteps, selectPol, records)
            return records

        else:
            return None

    def _measureNoiseTemp_SINGLE(self,
                fkCartTest: int,                
                freqLO: float,
                loIsLocked: bool, 
                freqIF: float,
                selectPol: SelectPolarization,
                records: dict[tuple[int, float], NoiseTempRawDatum]) -> None:
        
        self.measurementStatus.setStatusMessage(f"Measure noise temperature LO={freqLO:.2f} GHz, IF={freqIF:.2f} GHz...")
        self.powerDetect.configure(units = 'W', fast_mode = True)
        self.ifSystem.frequency = self.noiseTempSettings.ifStart
        self.ifSystem.attenuation = 22
        self.ifSystem.frequency = freqIF
        self.chopper.spin(self.settings.commonSettings.chopperSpeed)
        sampleInterval = 1 / self.settings.commonSettings.sampleRate
        openIsHot = self.chopper.openIsHot
        selectPol = SelectPolarization(self.noiseTempSettings.polarization)

        for pol in 0, 1:
            if selectPol.testPol(pol):
                for sideband in ('USB', 'LSB'):
                    self.ifSystem.set_pol_sideband(pol, sideband)
                    time.sleep(0.5)
                    self.dataDisplay.chopperPowerHistory = []
                    samplesHot = []
                    samplesCold = []                    
                    record = records.get((pol, freqIF), None)
                    if not record:
                        record = self._initRawDatum(fkCartTest, freqLO, loIsLocked, freqIF, pol)
                        records[(pol, freqIF)] = record
                    #select the IF record to be displayed to the user:
                    self.dataDisplay.currentNoiseTemp[pol] = record
                    
                    done = False
                    while not done:
                        cycleEnd = time.time() + sampleInterval
                        chopperPower = ChopperPowers(
                            inputName = self.ifSystem.input_select.name,
                            chopperState = self.chopper.getState(),
                            power = self.powerDetect.read()
                        )
                        self.dataDisplay.chopperPowerHistory.append(chopperPower)
                        if chopperPower.chopperState == ChopperState.OPEN:
                            if openIsHot:
                                samplesHot.append(chopperPower.power)
                            else:
                                samplesCold.append(chopperPower.power)    
                        elif chopperPower.chopperState == ChopperState.CLOSED:
                            if openIsHot:
                                samplesCold.append(chopperPower.power)
                            else:
                                samplesHot.append(chopperPower.power)    
        
                        if len(samplesHot) >= self.settings.commonSettings.powerMeterConfig.maxS and len(samplesCold) >= self.settings.commonSettings.powerMeterConfig.maxS:
                            done = True
                        elif len(samplesHot) >= self.settings.commonSettings.powerMeterConfig.minS and len(samplesCold) >= self.settings.commonSettings.powerMeterConfig.minS:
                            pHotErr = stdev(samplesHot) / sqrt(len(samplesHot))
                            pColdErr = stdev(samplesCold) / sqrt(len(samplesCold))
                            if pHotErr <= self.settings.commonSettings.powerMeterConfig.stdErr and pColdErr <= self.settings.commonSettings.powerMeterConfig.stdErr:
                                done = True
    
                        now = time.time()
                        if now < cycleEnd:
                            time.sleep(cycleEnd - now)

                    if sideband == 'USB':
                        record.Phot_USB = 10 * log10(mean(samplesHot) * 1000)
                        record.Pcold_USB = 10 * log10(mean(samplesCold) * 1000)
                        record.Phot_USB_StdErr = pHotErr
                        record.Pcold_USB_StdErr = pColdErr
                    else:
                        record.Phot_LSB = 10 * log10(mean(samplesHot) * 1000)
                        record.Pcold_LSB = 10 * log10(mean(samplesCold) * 1000)
                        record.Phot_LSB_StdErr = pHotErr
                        record.Pcold_LSB_StdErr = pColdErr

    def _measureNoiseTemp_SWEEP(self,
                freqLO: float,
                ifSteps: list[float],
                selectPol: SelectPolarization,
                records: dict[tuple[int, float], NoiseTempRawDatum]) -> None:

        self.measurementStatus.setStatusMessage(f"Measure noise temperature LO={freqLO:.2f} GHz...")
        self.chopper.stop()
        self.rfSrcDevice.turnOff()
        self.settings.ntSpecAnSettings.sweepPoints = int((self.noiseTempSettings.ifStop - self.noiseTempSettings.ifStart) / self.noiseTempSettings.ifStep) + 1
        self.powerDetect.configure(config = self.settings.ntSpecAnSettings, startGHz = self.noiseTempSettings.ifStart, stopGHz = self.noiseTempSettings.ifStop)
        selectPol = SelectPolarization(self.noiseTempSettings.polarization)
        
        for pol in 0, 1:
            if selectPol.testPol(pol):
                #select the IF record to be displayed to the user:
                self.dataDisplay.currentNoiseTemp[pol] = records[(pol, 6)]
                
                #prepare the traces to be displayed to the user:
                self.dataDisplay.specAnPowerHistory = SpecAnPowers(pol = pol, ifFreqs = ifSteps)

                self.chopper.gotoHot()

                self.ifSystem.set_pol_sideband(pol, 'USB')                        
                _, amps = self.powerDetect.read()

                self.dataDisplay.specAnPowerHistory.pHotUSB = amps

                for freqIF, amp in zip(ifSteps, amps):
                    records[(pol, freqIF)].Phot_USB = amp

                self.ifSystem.set_pol_sideband(pol, 'LSB')
                _, amps = self.powerDetect.read()

                self.dataDisplay.specAnPowerHistory.pHotLSB = amps

                for freqIF, amp in zip(ifSteps, amps):
                    records[(pol, freqIF)].Phot_LSB = amp

                self.chopper.gotoCold()
                
                self.ifSystem.set_pol_sideband(pol, 'USB')                        
                _, amps = self.powerDetect.read()

                self.dataDisplay.specAnPowerHistory.pColdUSB = amps

                for freqIF, amp in zip(ifSteps, amps):
                    records[(pol, freqIF)].Pcold_USB = amp

                self.ifSystem.set_pol_sideband(pol, 'LSB')
                _, amps = self.powerDetect.read()

                self.dataDisplay.specAnPowerHistory.pColdLSB = amps

                for freqIF, amp in zip(ifSteps, amps):
                    records[(pol, freqIF)].Pcold_LSB = amp

    def calcMeanNoiseTemp(self, records) -> float:
        if isinstance(records, dict):
            iterable = list(records.values())
        else:
            iterable = records

        sum = 0
        def calc(rec):
            nonlocal sum
            Y = (10 ** (rec.Phot_USB / 10)) / (10 ** (rec.Pcold_USB / 10))
            sum += (rec.TRF_Hot - self.settings.commonSettings.tColdEff * Y) / (Y - 1)
        
        map(calc, iterable)
        return sum / len(iterable)

#### IMAGE REJECTION #####################################
    
    def measureImageReject(self,
            fkCartTest: int,
            freqLO: float,
            loIsLocked: bool,
            freqIF: float,
            recordsIn: dict[tuple[int, float], NoiseTempRawDatum] | None = None
        ) -> dict[tuple[int, float], NoiseTempRawDatum] | None:
        
        self.chopper.gotoHot()
        self.ifSystem.output_select = OutputSelect.POWER_DETECT
        self.ifSystem.input_select = InputSelect.POL0_USB
        selectPol = SelectPolarization(self.noiseTempSettings.polarization)
        if recordsIn is not None:
            records = recordsIn
        else:
            records = {}

        if self.powerDetect.detect_mode == DetectMode.METER:
            self._measureImageReject_SINGLE(fkCartTest, freqLO, loIsLocked, freqIF, selectPol, records)
            return records
        
        elif self.powerDetect.detect_mode == DetectMode.SPEC_AN:
            self._measureImageReject_SWEEP(fkCartTest, freqLO, loIsLocked, freqIF, selectPol, records)
            return records

        else:
            return None

    def _measureImageReject_SINGLE(self,
            fkCartTest: int, 
            freqLO: float,
            loIsLocked: bool,
            freqIF: float,
            selectPol: SelectPolarization,
            records: dict[tuple[int, float], NoiseTempRawDatum]) -> None:

        self.measurementStatus.setStatusMessage(f"Measure image rejection LO={freqLO:.2f} GHz, IF={freqIF:.2f} GHz...")
        self.powerDetect.configure(units = 'dBm', fast_mode = False)

        for pol in (0, 1):
            if selectPol.testPol(pol):
                record = records.get((pol, freqIF), None)
                if not record:
                    record = self._initRawDatum(fkCartTest, freqLO, loIsLocked, freqIF, pol)
                    records[(pol, freqIF)] = record
                self.dataDisplay.currentNoiseTemp[pol] = record

                if record.Is_LO_Unlocked:
                    # can't take data if the LO is unlocked.
                    record.Is_RF_Unlocked = True
                    record.PwrUSB_SrcUSB = -100
                    record.PwrLSB_SrcUSB = -200
                    record.PwrLSB_SrcLSB = -100
                    record.PwrUSB_SrcLSB = -200
                
                else:
                    self.ifSystem.frequency = freqIF
                    self.measurementStatus.setStatusMessage(f"Locking RF source at {freqLO + freqIF:.2f} GHz...")
                    rfLocked, msg = self.rfSrcDevice.lockRF(self.rfReference, freqLO + freqIF, self.settings.commonSettings.sigGenAmplitude)
                
                    if not rfLocked:
                        # we can't take data if the RF is unlocked.
                        record.Is_RF_Unlocked = True
                        record.PwrUSB_SrcUSB = -100
                        record.PwrLSB_SrcUSB = -200
                    else:
                        record.Is_RF_Unlocked = False
                        self.ifSystem.set_pol_sideband(pol, 'USB')
                        time.sleep(0.25)                
                        success, msg = self.rfAutoLevel.autoLevel(freqIF, self.settings.commonSettings.imageRejectSBTarget_PM)
                        record.Source_Power_USB = self.rfSrcDevice.getPAVD()
                        record.PwrUSB_SrcUSB = self.powerDetect.read()
                        self.ifSystem.set_pol_sideband(pol, 'LSB')
                        time.sleep(0.25)                
                        record.PwrLSB_SrcUSB = self.powerDetect.read()

                    if msg:
                        self.logger.info(msg)
                    
                    self.measurementStatus.setStatusMessage(f"Locking RF source at {freqLO - freqIF:.2f} GHz...")
                    rfLocked, msg = self.rfSrcDevice.lockRF(self.rfReference, freqLO - freqIF, self.settings.commonSettings.sigGenAmplitude)

                    if not rfLocked:
                        # we can't take data if the RF is unlocked.
                        record.Is_RF_Unlocked = True
                        record.PwrLSB_SrcLSB = -100
                        record.PwrUSB_SrcLSB = -200                        
                    else:
                        record.Is_RF_Unlocked = False
                        self.ifSystem.set_pol_sideband(pol, 'LSB')
                        time.sleep(0.25)                
                        success, msg = self.rfAutoLevel.autoLevel(freqIF, self.settings.commonSettings.imageRejectSBTarget_PM)
                        record.Source_Power_LSB = self.rfSrcDevice.getPAVD()
                        record.PwrLSB_SrcLSB = self.powerDetect.read()
                        self.ifSystem.set_pol_sideband(pol, 'USB')
                        time.sleep(0.25)                
                        record.PwrUSB_SrcLSB = self.powerDetect.read()

                    if msg:
                        self.logger.info(msg)
        self.rfSrcDevice.turnOff()
        
    def _measureImageReject_SWEEP(self,
            fkCartTest: int, 
            freqLO: float,
            loIsLocked: bool,
            freqIF: float,
            selectPol: SelectPolarization,
            records: dict[tuple[int, float], NoiseTempRawDatum]) -> tuple[bool, str]:         
        
        self.powerDetect.configure(config = self.settings.irSpecAnSettings)            
        for pol in (0, 1):
            if selectPol.testPol(pol):
    
                if self.measurementStatus.stopNow():
                    self.rfSrcDevice.turnOff()
                    self.finished = True                
                    return True, "User stop"                

                record = records.get((pol, freqIF), None)
                if not record:
                    record = self._initRawDatum(fkCartTest, freqLO, loIsLocked, freqIF, pol)
                    records[(pol, freqIF)] = record
                self.dataDisplay.currentNoiseTemp[pol] = record

                if record.Is_LO_Unlocked:
                    # can't take data if the LO is unlocked.
                    record.Is_RF_Unlocked = True
                    record.PwrUSB_SrcUSB = -100
                    record.PwrLSB_SrcUSB = -200
                    record.PwrUSB_SrcUSB = -100
                    record.PwrLSB_SrcUSB = -200
                
                else:
                    self.ifSystem.frequency = freqIF
                    self.measurementStatus.setStatusMessage(f"Locking RF source at {freqLO + freqIF:.2f} GHz...")
                    rfLocked, msg = self.rfSrcDevice.lockRF(self.rfReference, freqLO + freqIF, self.settings.commonSettings.sigGenAmplitude)
                
                    if not rfLocked:
                        record.Is_RF_Unlocked = True
                        record.PwrUSB_SrcUSB = -100
                        record.PwrLSB_SrcUSB = -200                            
                    else:
                        record.Is_RF_Unlocked = False
                        self.ifSystem.set_pol_sideband(pol, 'USB')                            
                        time.sleep(0.25)                
                        success, msg = self.rfAutoLevel.autoLevel(freqIF, self.settings.commonSettings.imageRejectSBTarget_SA)
                        record.Source_Power_USB = self.rfSrcDevice.getPAVD()
                        record.PwrUSB_SrcUSB = self.powerDetect.read(averaging = 50, delay = 1.5)
                        self.ifSystem.set_pol_sideband(pol, 'LSB')
                        time.sleep(0.25)
                        record.PwrLSB_SrcUSB = self.powerDetect.read(averaging = 50, delay = 1.5)

                    if msg:
                        self.logger.info(msg)

                    if self.measurementStatus.stopNow():
                        self.rfSrcDevice.turnOff()
                        self.finished = True                
                        return True, "User stop"      
                    
                    self.measurementStatus.setStatusMessage(f"Locking RF source at {freqLO - freqIF:.2f} GHz...")
                    rfLocked, msg = self.rfSrcDevice.lockRF(self.rfReference, freqLO - freqIF, self.settings.commonSettings.sigGenAmplitude)
                    
                    if not rfLocked:
                        record.Is_RF_Unlocked = True
                        record.PwrLSB_SrcLSB = -100
                        record.PwrUSB_SrcLSB = -200
                    else:
                        record.Is_RF_Unlocked = False
                        self.ifSystem.set_pol_sideband(pol, 'LSB')                            
                        time.sleep(0.25)                
                        success, msg = self.rfAutoLevel.autoLevel(freqIF, self.settings.commonSettings.imageRejectSBTarget_SA)
                        record.Source_Power_LSB = self.rfSrcDevice.getPAVD()
                        record.PwrLSB_SrcLSB = self.powerDetect.read(averaging = 50, delay = 1.5)
                        self.ifSystem.set_pol_sideband(pol, 'USB')
                        time.sleep(0.25)
                        record.PwrUSB_SrcLSB = self.powerDetect.read(averaging = 50, delay = 1.5)
                        self.rfSrcDevice.turnOff()

                    if msg:
                        self.logger.info(msg)
                
                if self.measurementStatus.stopNow():
                    self.rfSrcDevice.turnOff()
                    self.finished = True                
                    return True, "User stop" 

        self.rfSrcDevice.turnOff()
        self.ifSystem.frequency = 0
        return True, ""

#### PRIVATE HELPER METHODS #######################################

    def _initRawData(self,
            fkCartTest: int,
            freqLO: float,
            loIsLocked: bool,
            selectPol: SelectPolarization,
            ifSteps: list[float]) -> dict[tuple[int, float], NoiseTempRawDatum]:
        
        try:
            tAmb, tErr = self.tempMonitor.readSingle(self.settings.commonSettings.sensorAmbient)
        except:
            tAmb = 0

        try:
            cartridgeTemps = self.receiver.ccaDevice.getCartridgeTemps()
        except:
            cartridgeTemps = None

        pll = self.receiver.loDevice.getPLL()
        lockInfo = self.receiver.loDevice.getLockInfo() #redundant
        pa = self.receiver.loDevice.getPA()
        if selectPol.testPol(0):
            sis01 = self.receiver.ccaDevice.getSIS(pol = 0, sis = 1, averaging = 8)
            sis02 = self.receiver.ccaDevice.getSIS(pol = 0, sis = 2, averaging = 8)
        if selectPol.testPol(1):
            sis11 = self.receiver.ccaDevice.getSIS(pol = 1, sis = 1, averaging = 8)
            sis12 = self.receiver.ccaDevice.getSIS(pol = 1, sis = 2, averaging = 8)
        now = datetime.now()
        records = {}

        for freqIF in ifSteps:            
            if selectPol.testPol(0):
                records[(0, freqIF)] = NoiseTempRawDatum(
                    fkCartTest = fkCartTest,
                    timeStamp = now,
                    FreqLO = freqLO,
                    CenterIF = freqIF,
                    BWIF = 100,
                    Pol = 0,
                    TRF_Hot = tAmb,
                    IF_Attn = self.ifSystem.attenuation,
                    TColdLoad = self.settings.commonSettings.tColdEff,
                    Vj1 = sis01['Vj'],
                    Ij1 = sis01['Ij'],
                    Imag = sis01['Imag'],
                    Vj2 = sis02['Vj'],
                    Ij2 = sis02['Ij'],
                    Tmixer = cartridgeTemps['temp2'] if cartridgeTemps else -1,
                    PLL_Lock_V = lockInfo['lockVoltage'],
                    PLL_Corr_V = lockInfo['corrV'],
                    PLL_Assm_T = pll['temperature'],
                    PA_A_Drain_V = pa['VDp0'],
                    PA_B_Drain_V = pa['VDp1'],
                    Is_LO_Unlocked = not loIsLocked
                )
            
            if selectPol.testPol(1):
                records[(1, freqIF)] = NoiseTempRawDatum(
                    fkCartTest = fkCartTest,
                    timeStamp = now,
                    FreqLO = freqLO,
                    CenterIF = freqIF,
                    BWIF = 100,
                    Pol = 1,
                    TRF_Hot = tAmb,
                    IF_Attn = self.ifSystem.attenuation,
                    TColdLoad = self.settings.commonSettings.tColdEff,
                    Vj1 = sis11['Vj'],
                    Ij1 = sis11['Ij'],
                    Imag = sis11['Imag'],
                    Vj2 = sis12['Vj'],
                    Ij2 = sis12['Ij'],
                    Tmixer = cartridgeTemps['temp5'] if cartridgeTemps else -1,
                    PLL_Lock_V = lockInfo['lockVoltage'],
                    PLL_Corr_V = lockInfo['corrV'],
                    PLL_Assm_T = pll['temperature'],
                    PA_A_Drain_V = pa['VDp0'],
                    PA_B_Drain_V = pa['VDp1'],
                    Is_LO_Unlocked = not loIsLocked
                )
        return records
    
    def _initRawDatum(self,
            fkCartTest: int,
            freqLO: float,
            loIsLocked: bool,
            freqIF: float,
            pol: int) -> NoiseTempRawDatum:
                
        try:
            tAmb, tErr = self.tempMonitor.readSingle(self.settings.commonSettings.sensorAmbient)
        except:
            tAmb = 0

        try:
            cartridgeTemps = self.receiver.ccaDevice.getCartridgeTemps()
        except:
            cartridgeTemps = None

        pll = self.receiver.loDevice.getPLL()
        lockInfo = self.receiver.loDevice.getLockInfo() #redundant
        pa = self.receiver.loDevice.getPA()
        sis1 = self.receiver.ccaDevice.getSIS(pol = pol, sis = 1, averaging = 8)
        sis2 = self.receiver.ccaDevice.getSIS(pol = pol, sis = 2, averaging = 8)
        now = datetime.now()

        return NoiseTempRawDatum(
            fkCartTest = fkCartTest,
            timeStamp = now,
            FreqLO = freqLO,
            CenterIF = freqIF,
            BWIF = 100,
            Pol = pol,
            TRF_Hot = tAmb,
            IF_Attn = self.ifSystem.attenuation,
            TColdLoad = self.settings.commonSettings.tColdEff,
            Vj1 = sis1['Vj'],
            Ij1 = sis1['Ij'],
            Imag = sis1['Imag'],
            Vj2 = sis2['Vj'],
            Ij2 = sis2['Ij'],
            Tmixer = cartridgeTemps['temp2'] if cartridgeTemps else -1,
            PLL_Lock_V = lockInfo['lockVoltage'],
            PLL_Corr_V = lockInfo['corrV'],
            PLL_Assm_T = pll['temperature'],
            PA_A_Drain_V = pa['VDp0'],
            PA_B_Drain_V = pa['VDp1'],
            Is_LO_Unlocked = not loIsLocked
        )
