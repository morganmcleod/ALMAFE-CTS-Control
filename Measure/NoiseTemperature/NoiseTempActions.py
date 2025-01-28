import time
from datetime import datetime
import logging
from typing import Optional
from statistics import mean, stdev
from math import sqrt, log10
from INSTR.SignalGenerator.Keysight_PSG_MXG import SignalGenerator
from INSTR.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from INSTR.PowerSupply.AgilentE363xA import PowerSupply
from INSTR.Chopper.Interface import Chopper_Interface, ChopperState
from INSTR.ColdLoad.AMI1720 import AMI1720
from Controllers.Receiver.CartAssembly import CartAssembly
from Controllers.Receiver.MixerAssembly import MixerAssembly
from Controllers.RFSource.CTS import RFSource
from Controllers.IFSystem.Interface import IFSystem_Interface, InputSelect, OutputSelect
from Controllers.PowerDetect.Interface import PowerDetect_Interface, DetectMode
from Controllers.IFAutoLevel import IFAutoLevel
from Controllers.RFAutoLevel import RFAutoLevel
from Measure.Shared.MeasurementStatus import MeasurementStatus
from Measure.Shared.DataDisplay import DataDisplay
from Measure.Shared.makeSteps import makeSteps
from Measure.Shared.SelectPolarization import SelectPolarization
from Measure.Shared.Sampler import Sampler
from Measure.Shared.SelectSIS import SelectSIS
from Measure.NoiseTemperature.SettingsContainer import SettingsContainer
from .schemas import CommonSettings, WarmIFSettings, NoiseTempSettings, YFactorSettings, ChopperPowers, \
    SpecAnPowers, YFactorSample, BiasOptSettings, YFactorPowers
from DBBand6Cart.schemas.WarmIFNoise import WarmIFNoise
from DBBand6Cart.schemas.NoiseTempRawDatum import NoiseTempRawDatum
from DBBand6Cart.schemas.DUT_Type import DUT_Type

class NoiseTempActions():

    def __init__(self,
            dutType: DUT_Type,
            loReference: SignalGenerator,
            rfReference: SignalGenerator,
            receiver: CartAssembly | MixerAssembly,
            rfSrcDevice: RFSource,
            ifSystem: IFSystem_Interface,
            powerDetect: PowerDetect_Interface,
            tempMonitor: TemperatureMonitor,
            powerSupply: Optional[PowerSupply],     # not used in MTS-2
            coldLoadController: AMI1720,
            chopper: Chopper_Interface,
            measurementStatus: MeasurementStatus,
            dataDisplay: DataDisplay,
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
        self._reset()

    def _reset(self) -> None:
        self.finished = False
        self.dataDisplay.reset()

    def start(self, noiseTempSettings: NoiseTempSettings):
        self._reset()
        self.noiseTempSettings = noiseTempSettings        
        self.measurementStatus.setComplete(False)
        self.measurementStatus.setStatusMessage("Started")

    def stop(self):        
        self.measurementStatus.stopMeasuring()
        self.measurementStatus.setComplete(True)
        self.chopper.stop()
        self.rfSrcDevice.setOutputPower(0)

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

    def setLO(self, 
            freqLO: float, 
            lockLO: bool = True, 
            setBias: bool = True,
        ) -> tuple[bool, str]:

        self.receiver.settings.loSettings.lockLO = lockLO
        msg = "Locking" if lockLO else "Tuning"
        msg += f" LO at {freqLO:.2f} GHz..."
        self.measurementStatus.setStatusMessage(msg)
        success, msg = self.receiver.setFrequency(freqLO, self.receiver.settings.loSettings)

        if not success:
            self.logger.error(msg)
        elif msg:
            self.logger.info(msg)

        if setBias:
            success, msg = self.receiver.setBias(freqLO)
            if not success:
                return False, "setBias failed. Provide config ID?"
            
            self.measurementStatus.setStatusMessage(f"Setting LO power...")
            selectPol = SelectPolarization(self.noiseTempSettings.polarization)
            success, msg = self.receiver.autoLOPower(pol0 = selectPol.testPol(0), pol1 = selectPol.testPol(1))
            if not success:
                return False, "cartAssembly.autoLOPower failed"

        if success:
            return True, f"Locked LO {'and set bias ' if setBias else ''}at {freqLO:.2f} GHz."
        else:
            return True, f"LO LOCK FAILED {'and set bias ' if setBias else ''}at {freqLO:.2f} GHz."

    def getLO(self) -> float:
        return self.receiver.freqLOGHz

    def setIF(self, freqIF: float = 0, ifAutoLevel: bool = True) -> tuple[bool, str]:

        self.ifSystem.frequency = freqIF

        success, msg = True, ""
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
            fkTestRecord: int, 
            warmIFSettings: WarmIFSettings) -> list[WarmIFNoise]:
        if self.powerSupply is not None:
            self.powerSupply.setOutputEnable(False)
            self.powerSupply.setVoltage(warmIFSettings.diodeVoltage)
            self.powerSupply.setCurrentLimit(warmIFSettings.diodeCurrentLimit)
            self.ifSystem.input_select = InputSelect.NOISE_SOURCE
        self.ifSystem.output_select = OutputSelect.POWER_DETECT
            
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
                    tIFCold, err = self.tempMonitor.readSingle(1)
                    tIFHot, err = self.tempMonitor.readSingle(3)
                    record = WarmIFNoise(
                        fkCartTest = fkTestRecord,
                        fkDUT_Type = self.dutType,
                        freqYig = freq,
                        atten = atten,
                        pHot = pHot,
                        pCold = pCold,
                        tAmbient = ambient,
                        tIFCold = tIFCold,
                        tIFHot = tIFHot,
                        noiseDiodeENR = warmIFSettings.diodeEnr
                    )
                    records.append(record)
        
        elif self.powerDetect.detect_mode == DetectMode.SPEC_AN:
            ### External switch and spectrum analyzer ###
            self.measurementStatus.setStatusMessage("Measuring IF System Noise")
            self.settings.ntSpecAnSettings.sweepPoints = int((warmIFSettings.ifStop - warmIFSettings.ifStart) / warmIFSettings.ifStep) + 1                
            self.powerDetect.configure(config = self.settings.ntSpecAnSettings, startGHz = warmIFSettings.ifStart, stopGHz = warmIFSettings.ifStop)

            # measure hot load:
            if self.powerSupply is not None:
                self.powerSupply.setOutputEnable(True)
            else:
                self.ifSystem.input_select = InputSelect.HOT_LOAD

            time.sleep(0.25)
            x, pHots = self.powerDetect.read()

            # measure cold load:
            if self.powerSupply is not None:
                self.powerSupply.setOutputEnable(False)
            else:
                self.ifSystem.input_select = InputSelect.COLD_LOAD

            time.sleep(0.25)
            x, pColds = self.powerDetect.read()

            ambient, err = self.tempMonitor.readSingle(self.settings.commonSettings.sensorAmbient)
            tIFCold, err = self.tempMonitor.readSingle(1)
            tIFHot, err = self.tempMonitor.readSingle(3)

            for freq, pHot, pCold in zip(x, pHots, pColds):
                records.append(
                    WarmIFNoise(
                        fkCartTest = fkTestRecord,
                        fkDUT_Type = self.dutType,
                        freqYig = freq / 1e9,
                        atten = 0,
                        pHot = 10 ** (pHot / 10) / 1000,
                        pCold = 10 ** (pCold / 10) / 1000,
                        tIFCold = tIFCold,
                        tIFHot = tIFHot,
                        tAmbient = ambient,
                        noiseDiodeENR = warmIFSettings.diodeEnr
                    )   
                )                

        self.measurementStatus.setStatusMessage("Warm IF Noise: Done.")
        self.dataDisplay.warmIfData = records
        return records
    
#### Y-FACTOR #####################################################

    def measureYFactor(self, settings: YFactorSettings) -> None:

        self.dataDisplay.yFactorHistory = []
        self.dataDisplay.yFactorPowers = []

        if self.powerDetect.detect_mode == DetectMode.METER or settings.detectMode == DetectMode.METER:
            return self._measureYFactor_SINGLE(settings)
        elif self.powerDetect.detect_mode == DetectMode.SPEC_AN or settings.detectMode == DetectMode.SPEC_AN:
            return self._measureYFactor_SWEEP(settings)
        else:
            return None
        
    def _measureYFactor_SINGLE(self, settings: YFactorSettings) -> None:

        self.measurementStatus.setStatusMessage("Y-factor started")
        self.measurementStatus.setComplete(False)
        self.chopper.spin(self.settings.commonSettings.chopperSpeed)
        self.powerDetect.configure(units = 'dBm', fast_mode = False)
        self.ifSystem.output_select = OutputSelect.POWER_DETECT
        self.ifSystem.input_select = settings.inputSelect

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

    def _measureYFactor_SWEEP(self, settings: YFactorSettings) -> None:
        self.measurementStatus.setStatusMessage("Y-factor started")
        self.measurementStatus.setComplete(False)
        self.ifSystem.output_select = OutputSelect.POWER_DETECT
        self.ifSystem.input_select = settings.inputSelect
        self.chopper.stop()
        self.chopper.gotoCold()
        
        self.powerDetect.configure(
            config = self.settings.ntSpecAnSettings, 
            startGHz = settings.ifStart, 
            stopGHz = settings.ifStop,
            sweepPoints = 10 * int(settings.ifStop - settings.ifStart) + 1)
        
        # set the analyzer for band power measurement:
        self.ifSystem.frequency = settings.ifStart + (settings.ifStop - settings.ifStart) / 2
        self.ifSystem.bandwidth = settings.ifStop - settings.ifStart

        retain_samples = 20
        chopperPowers = []

        def read():
            self.chopper.gotoHot()
            time.sleep(0.5)
            chopperPowers.append(
                ChopperPowers(
                    inputName = self.ifSystem.input_select.name, 
                    chopperState = ChopperState.OPEN, 
                    power = self.powerDetect.read()
                )
            )
            self.chopper.gotoCold()
            time.sleep(0.5)
            chopperPowers.append(
                ChopperPowers(
                    inputName = self.ifSystem.input_select.name, 
                    chopperState = ChopperState.CLOSED, 
                    power = self.powerDetect.read()
                )
            )

        # measure how long hot, cold sweeps take
        timeStart = time.time()
        read()
        sampling_interval = (time.time() - timeStart) * 1.2
        # discard the sample used for measuring:
        chopperPowers = []

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
                time.sleep(2 * sampling_interval)
        
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
        if self.chopper.openIsHot:
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
            fkTestRecord: int,
            freqLO: float,
            freqIF: float = 0,
            recordsIn: dict[tuple[int, float], NoiseTempRawDatum] | None = None,
            statusMessage: str = None
        ) -> dict[tuple[int, float], NoiseTempRawDatum] | None:
        self.rfSrcDevice.setOutputPower(0)
        self.ifSystem.output_select = OutputSelect.POWER_DETECT
        self.ifSystem.input_select = InputSelect.POL0_USB
        selectPol = SelectPolarization(self.noiseTempSettings.polarization)

        if self.powerDetect.detect_mode == DetectMode.METER:
            
            if recordsIn is not None:
                records = recordsIn
            else:
                records = {}
            self._measureNoiseTemp_SINGLE(fkTestRecord, freqLO, freqIF, selectPol, records, statusMessage)
            return records
        
        elif self.powerDetect.detect_mode == DetectMode.SPEC_AN:
            ifSteps = makeSteps(self.noiseTempSettings.ifStart, self.noiseTempSettings.ifStop, self.noiseTempSettings.ifStep)
            if recordsIn is not None:
                records = recordsIn
            else:
                records = self._initRawData(fkTestRecord, freqLO, selectPol, ifSteps)
            self._measureNoiseTemp_SWEEP(freqLO, ifSteps, selectPol, records, statusMessage)
            return records

        else:
            return None

    def _measureNoiseTemp_SINGLE(self,
                fkTestRecord: int,                
                freqLO: float,
                freqIF: float,
                selectPol: SelectPolarization,
                records: dict[tuple[int, float], NoiseTempRawDatum],
                statusMessage: str = None
            ) -> None:
        if statusMessage is None:
            statusMessage = f"Measure noise temperature LO={freqLO:.2f} GHz, IF={freqIF:.2f} GHz..."        
        self.measurementStatus.setStatusMessage(statusMessage)
        self.powerDetect.configure(units = 'W', fast_mode = True)
        self.ifSystem.frequency = self.noiseTempSettings.ifStart
        self.ifSystem.attenuation = 22
        self.ifSystem.frequency = freqIF
        self.chopper.spin(self.settings.commonSettings.chopperSpeed)
        sampleInterval = 1 / self.settings.commonSettings.sampleRate
        openIsHot = self.chopper.openIsHot
        selectPol = SelectPolarization(self.noiseTempSettings.polarization)

        sidebands = ('USB', 'LSB') if self.receiver.is2SB() else ('USB')

        for pol in 0, 1:
            if selectPol.testPol(pol):
                for sideband in sidebands:
                    self.ifSystem.set_pol_sideband(pol, sideband)
                    time.sleep(0.5)
                    self.dataDisplay.chopperPowerHistory = []
                    samplesHot = []
                    samplesCold = []                    
                    record = records.get((pol, freqIF), None)
                    if not record:
                        record = self._initRawDatum(fkTestRecord, freqLO, freqIF, pol)
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
                records: dict[tuple[int, float], NoiseTempRawDatum],
                statusMessage: str = None
            ) -> None:
        if statusMessage is None:
            statusMessage = f"Measure noise temperature LO={freqLO:.2f} GHz..."
        self.measurementStatus.setStatusMessage(statusMessage)
        self.chopper.stop()
        self.rfSrcDevice.setOutputPower(0)
        self.settings.ntSpecAnSettings.sweepPoints = int((self.noiseTempSettings.ifStop - self.noiseTempSettings.ifStart) / self.noiseTempSettings.ifStep) + 1
        self.powerDetect.configure(config = self.settings.ntSpecAnSettings, startGHz = self.noiseTempSettings.ifStart, stopGHz = self.noiseTempSettings.ifStop)
                
        for pol in 0, 1:
            if selectPol.testPol(pol):
                #select the IF record to be displayed to the user:
                self.dataDisplay.currentNoiseTemp[pol] = records[(pol, ifSteps[0])]
                
                #prepare the traces to be displayed to the user:
                self.dataDisplay.specAnPowerHistory = SpecAnPowers(pol = pol, ifFreqs = ifSteps)

                self.chopper.gotoHot()

                self.ifSystem.set_pol_sideband(pol, 'USB')                        
                _, amps = self.powerDetect.read()

                self.dataDisplay.specAnPowerHistory.pHotUSB = amps

                for freqIF, amp in zip(ifSteps, amps):
                    records[(pol, freqIF)].Phot_USB = amp

                if self.receiver.is2SB():
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

                if self.receiver.is2SB():
                    self.ifSystem.set_pol_sideband(pol, 'LSB')
                    _, amps = self.powerDetect.read()

                    self.dataDisplay.specAnPowerHistory.pColdLSB = amps

                    for freqIF, amp in zip(ifSteps, amps):
                        records[(pol, freqIF)].Pcold_LSB = amp

    def calcMeanNoiseTemp(self, 
            records: NoiseTempRawDatum, 
            ifStart: float, 
            ifStop: float
        ) -> float:
        if isinstance(records, dict):
            _records = list(records.values())
        else:
            _records = records

        sum = 0
        _records = [rec for rec in _records if ifStart <= rec.CenterIF <= ifStop]
        for rec in _records:
            Y = (10 ** (rec.Phot_USB / 10)) / (10 ** (rec.Pcold_USB / 10))
            sum += (rec.TRF_Hot - self.settings.commonSettings.tColdEff * Y) / (Y - 1)
        return sum / len(_records)

#### IMAGE REJECTION #####################################
    
    def measureImageReject(self,
            fkTestRecord: int,
            freqLO: float,
            freqIF: float,
            recordsIn: dict[tuple[int, float], NoiseTempRawDatum] | None = None
            ) -> dict[tuple[int, float], NoiseTempRawDatum] | None:
        
        if not self.receiver.is2SB():
            return None

        self.chopper.gotoHot()
        self.ifSystem.output_select = OutputSelect.POWER_DETECT
        self.ifSystem.input_select = InputSelect.POL0_USB
        selectPol = SelectPolarization(self.noiseTempSettings.polarization)
        if recordsIn is not None:
            records = recordsIn
        else:
            records = {}

        if self.powerDetect.detect_mode == DetectMode.METER:
            self._measureImageReject_SINGLE(fkTestRecord, freqLO, freqIF, selectPol, records)
            return records
        
        elif self.powerDetect.detect_mode == DetectMode.SPEC_AN:
            self._measureImageReject_SWEEP(fkTestRecord, freqLO, freqIF, selectPol, records)
            return records

        else:
            return None

    def _measureImageReject_SINGLE(self,
            fkTestRecord: int, 
            freqLO: float,
            freqIF: float,
            selectPol: SelectPolarization,
            records: dict[tuple[int, float], NoiseTempRawDatum]) -> None:

        self.measurementStatus.setStatusMessage(f"Measure image rejection LO={freqLO:.2f} GHz, IF={freqIF:.2f} GHz...")
        self.powerDetect.configure(units = 'dBm', fast_mode = False)

        for pol in (0, 1):
            if selectPol.testPol(pol):
                record = records.get((pol, freqIF), None)
                if not record:
                    record = self._initRawDatum(fkTestRecord, freqLO, freqIF, pol)
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
                    rfLocked, msg = self.rfSrcDevice.lockRF(freqLO + freqIF, self.settings.commonSettings.rfRefAmplitude)
                
                    if not rfLocked:
                        # we can't take data if the RF is unlocked.
                        record.Is_RF_Unlocked = True
                        record.PwrUSB_SrcUSB = -100
                        record.PwrLSB_SrcUSB = -200
                    else:
                        record.Is_RF_Unlocked = False
                        self.ifSystem.set_pol_sideband(pol, 'USB')
                        time.sleep(0.25)                
                        success, msg = self.rfSrcDevice.autoRFPower(self.powerDetect, self.settings.commonSettings.imageRejectSBTarget_SA)
                        record.Source_Power_USB = self.rfSrcDevice.getPAVD()
                        record.PwrUSB_SrcUSB = self.powerDetect.read()
                        self.ifSystem.set_pol_sideband(pol, 'LSB')
                        time.sleep(0.25)                
                        record.PwrLSB_SrcUSB = self.powerDetect.read()

                    self.measurementStatus.setStatusMessage(f"Locking RF source at {freqLO - freqIF:.2f} GHz...")
                    rfLocked, msg = self.rfSrcDevice.lockRF(freqLO - freqIF, self.settings.commonSettings.rfRefAmplitude)

                    if not rfLocked:
                        # we can't take data if the RF is unlocked.
                        record.Is_RF_Unlocked = True
                        record.PwrLSB_SrcLSB = -100
                        record.PwrUSB_SrcLSB = -200                        
                    else:
                        record.Is_RF_Unlocked = False
                        self.ifSystem.set_pol_sideband(pol, 'LSB')
                        time.sleep(0.25)                
                        success, msg = self.rfSrcDevice.autoRFPower(self.powerDetect, self.settings.commonSettings.imageRejectSBTarget_SA)
                        record.Source_Power_LSB = self.rfSrcDevice.getPAVD()
                        record.PwrLSB_SrcLSB = self.powerDetect.read()
                        self.ifSystem.set_pol_sideband(pol, 'USB')
                        time.sleep(0.25)                
                        record.PwrUSB_SrcLSB = self.powerDetect.read()

        self.rfSrcDevice.setOutputPower(0)
        
    def _measureImageReject_SWEEP(self,
            fkTestRecord: int, 
            freqLO: float,
            freqIF: float,
            selectPol: SelectPolarization,
            records: dict[tuple[int, float], NoiseTempRawDatum]) -> tuple[bool, str]:         
        
        self.powerDetect.configure(config = self.settings.irSpecAnSettings)            
        for pol in (0, 1):
            if selectPol.testPol(pol):
    
                if self.measurementStatus.stopNow():
                    self.rfSrcDevice.setOutputPower(0)
                    self.finished = True                
                    return True, "User stop"                

                record = records.get((pol, freqIF), None)
                if not record:
                    record = self._initRawDatum(fkTestRecord, freqLO, freqIF, pol)
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
                    rfLocked, msg = self.rfSrcDevice.setFrequency(freqLO + freqIF)
                          
                    if not rfLocked:
                        self.measurementStatus.setStatusMessage(msg, error = True)
                        record.Is_RF_Unlocked = True
                        record.PwrUSB_SrcUSB = -100
                        record.PwrLSB_SrcUSB = -200
                    else:
                        self.measurementStatus.setStatusMessage("")
                        record.Is_RF_Unlocked = False
                        self.ifSystem.set_pol_sideband(pol, 'USB')                            
                        time.sleep(0.2)
                        success, msg = self.rfSrcDevice.autoRFPower(self.powerDetect, self.settings.commonSettings.imageRejectSBTarget_SA)                        
                        record.Source_Power_USB = self.rfSrcDevice.getPAVD()
                        if not success:
                            self.measurementStatus.setStatusMessage(msg, error = True)
                            record.PwrUSB_SrcUSB = -100
                            record.PwrLSB_SrcUSB = -200
                        else:
                            self.measurementStatus.setStatusMessage("")
                            record.PwrUSB_SrcUSB = self.powerDetect.read(averaging = 100, delay = 1)
                            self.ifSystem.set_pol_sideband(pol, 'LSB')
                            time.sleep(0.2)
                            record.PwrLSB_SrcUSB = self.powerDetect.read(averaging = 100, delay = 1)

                    if self.measurementStatus.stopNow():
                        self.rfSrcDevice.setOutputPower(0)
                        self.finished = True                
                        return True, "User stop"      
                    
                    self.measurementStatus.setStatusMessage(f"Locking RF source at {freqLO - freqIF:.2f} GHz...")
                    rfLocked, msg = self.rfSrcDevice.setFrequency(freqLO - freqIF)

                    if not rfLocked:
                        self.measurementStatus.setStatusMessage(msg, error = True)
                        record.Is_RF_Unlocked = True
                        record.PwrLSB_SrcLSB = -100
                        record.PwrUSB_SrcLSB = -200
                    else:
                        self.measurementStatus.setStatusMessage("")
                        record.Is_RF_Unlocked = False
                        self.ifSystem.set_pol_sideband(pol, 'LSB')                            
                        time.sleep(0.2)
                        success, msg = self.rfSrcDevice.autoRFPower(self.powerDetect, self.settings.commonSettings.imageRejectSBTarget_SA)
                        record.Source_Power_LSB = self.rfSrcDevice.getPAVD()
                        if not success:
                            self.measurementStatus.setStatusMessage(msg, error = True)
                            record.PwrLSB_SrcLSB = -100
                            record.PwrUSB_SrcLSB = -200
                        else:
                            self.measurementStatus.setStatusMessage("")
                            record.PwrLSB_SrcLSB = self.powerDetect.read(averaging = 100, delay = 1)
                            self.ifSystem.set_pol_sideband(pol, 'USB')
                            time.sleep(0.2)
                            record.PwrUSB_SrcLSB = self.powerDetect.read(averaging = 100, delay = 1)
                        
                    self.rfSrcDevice.setOutputPower(0)
                
                if self.measurementStatus.stopNow():
                    self.rfSrcDevice.setOutputPower(0)
                    self.finished = True                
                    return True, "User stop" 

        self.rfSrcDevice.setOutputPower(0)
        self.ifSystem.frequency = 0
        return True, ""

#### PRIVATE HELPER METHODS #######################################

    def _initRawData(self,
            fkTestRecord: int,
            freqLO: float,
            selectPol: SelectPolarization,
            ifSteps: list[float]) -> dict[tuple[int, float], NoiseTempRawDatum]:


        loIsLocked = self.receiver.isLocked()        

        try:
            tAmb, tErr = self.tempMonitor.readSingle(self.settings.commonSettings.sensorAmbient)
        except:
            tAmb = 0

        try:
            tMixer, tErr = self.tempMonitor.readSingle(self.settings.commonSettings.sensorMixer)
        except:
            tMixer = 0

        try:
            cartridgeTemps = self.receiver.ccaDevice.getCartridgeTemps()
        except:
            cartridgeTemps = None

        pll = self.receiver.getPLL()
        pa = self.receiver.getPA()
        if selectPol.testPol(0):
            sis01 = self.receiver.readSISBias(SelectSIS.SIS1, pol = 0, averaging = 8)
            sis02 = self.receiver.readSISBias(SelectSIS.SIS2, pol = 0, averaging = 8)
        if selectPol.testPol(1):
            sis11 = self.receiver.readSISBias(SelectSIS.SIS1, pol = 1, averaging = 8)
            sis12 = self.receiver.readSISBias(SelectSIS.SIS2, pol = 1, averaging = 8)
        now = datetime.now()
        records = {}

        for freqIF in ifSteps:            
            if selectPol.testPol(0):
                records[(0, freqIF)] = NoiseTempRawDatum(
                    fkCartTest = fkTestRecord,
                    fkDUT_Type = self.dutType.value,
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
                    Tmixer = cartridgeTemps['temp2'] if cartridgeTemps else tMixer,
                    PLL_Lock_V = pll['lockVoltage'],
                    PLL_Corr_V = pll['corrV'],
                    PLL_Assm_T = pll['temperature'],
                    PA_A_Drain_V = pa['VDp0'],
                    PA_B_Drain_V = pa['VDp1'],
                    Is_LO_Unlocked = not loIsLocked
                )
            
            if selectPol.testPol(1):
                records[(1, freqIF)] = NoiseTempRawDatum(
                    fkCartTest = fkTestRecord,
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
                    Tmixer = cartridgeTemps['temp5'] if cartridgeTemps else tMixer,
                    PLL_Lock_V = pll['lockVoltage'],
                    PLL_Corr_V = pll['corrV'],
                    PLL_Assm_T = pll['temperature'],
                    PA_A_Drain_V = pa['VDp0'],
                    PA_B_Drain_V = pa['VDp1'],
                    Is_LO_Unlocked = not loIsLocked
                )
        return records
    
    def _initRawDatum(self,
            fkTestRecord: int,
            freqLO: float,
            freqIF: float,
            pol: int) -> NoiseTempRawDatum:

        loIsLocked = self.receiver.isLocked()  
            
        try:
            tAmb, tErr = self.tempMonitor.readSingle(self.settings.commonSettings.sensorAmbient)
        except:
            tAmb = 0

        try:
            cartridgeTemps = self.receiver.ccaDevice.getCartridgeTemps()
        except:
            cartridgeTemps = None

        pll = self.receiver.getPLL()
        pa = self.receiver.getPA()
        sis1 = self.receiver.readSISBias(SelectSIS.SIS1, pol = pol, averaging = 8)
        sis2 = self.receiver.readSISBias(SelectSIS.SIS2, pol = pol, averaging = 8)
        now = datetime.now()

        return NoiseTempRawDatum(
            fkCartTest = fkTestRecord,
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
            PLL_Lock_V = pll['lockVoltage'],
            PLL_Corr_V = pll['corrV'],
            PLL_Assm_T = pll['temperature'],
            PA_A_Drain_V = pa['VDp0'],
            PA_B_Drain_V = pa['VDp1'],
            Is_LO_Unlocked = not loIsLocked
        )
