from CTSDevices.WarmIFPlate.WarmIFPlate import WarmIFPlate
from CTSDevices.WarmIFPlate.InputSwitch import InputSelect
from CTSDevices.WarmIFPlate.OutputSwitch import OutputSelect, LoadSelect, PadSelect
from CTSDevices.PowerMeter.KeysightE441X import PowerMeter, Unit
from CTSDevices.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from CTSDevices.Chopper.Band6Chopper import Chopper, State
from CTSDevices.SignalGenerator.Keysight_PSG_MXG import SignalGenerator
from CTSDevices.FEMC.CartAssembly import CartAssembly
from CTSDevices.FEMC.RFSource import RFSource
from CTSDevices.ColdLoad.AMI1720 import AMI1720
from CTSDevices.Common.BinarySearchController import BinarySearchController
from DBBand6Cart.schemas.NoiseTempRawDatum import NoiseTempRawDatum
from DBBand6Cart.NoiseTempRawData import NoiseTempRawData
from app.database.CTSDB import CTSDB
from ..Shared.makeSteps import makeSteps
from ..Shared.MeasurementStatus import MeasurementStatus
from .schemas import ChopperPowers

from DebugOptions import *

import concurrent.futures
import logging
import time
from datetime import datetime
from typing import Tuple
from statistics import mean, stdev
from math import sqrt, log10
import copy

class NoiseTemperature():

    def __init__(self,
            loReference: SignalGenerator,
            rfReference: SignalGenerator,
            cartAssembly: CartAssembly,
            rfSrcDevice: RFSource,
            warmIFPlate: WarmIFPlate,
            powerMeter: PowerMeter,
            tempMonitor: TemperatureMonitor,
            coldLoadController: AMI1720,
            chopper: Chopper,
            measurementStatus: MeasurementStatus):
        
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.loReference = loReference
        self.rfReference = rfReference
        self.cartAssembly = cartAssembly
        self.rfSrcDevice = rfSrcDevice        
        self.warmIFPlate = warmIFPlate
        self.powerMeter = powerMeter
        self.tempMonitor = tempMonitor
        self.coldLoadController = coldLoadController
        self.chopper = chopper
        self.measurementStatus = measurementStatus
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers = 1)
        self.commonSettings = None
        self.settings = None
        self.chopperPowerHistory = []
        self.rawDataRecords = None
        self.__reset()        

    def __reset(self):
        self.ntRawData = NoiseTempRawData(driver = CTSDB())
        self.keyCartTest = 0
        self.stopNow = False
        self.finished = False
        self.ifAtten = 22
        self.chopperPowerHistory = []
        self.rawDataRecords = None
        
    def updateSettings(self, commonSettings = None):
        if commonSettings is not None:
            self.commonSettings = commonSettings

    def start(self, keyCartTest: int, doImageReject: bool):
        self.__reset()
        self.keyCartTest = keyCartTest
        self.doNoiseTemp = True
        self.doImageReject = doImageReject
        self.coldLoadController.startFill()
        self.futures = []
        self.futures.append(self.executor.submit(self.__run))
        concurrent.futures.wait(self.futures)
        self.coldLoadController.stopFill()
        self.chopper.stop()
        self.__rfSourceOff()
        self.powerMeter.setUnits(Unit.DBM)
        self.powerMeter.setFastMode(False)

    def stop(self):
        self.stopNow = True

    def isMeasuring(self):
        return not self.finished

    def __run(self) -> None:
        self.chopper.stop()
        loSteps = makeSteps(self.settings.loStart, self.settings.loStop, self.settings.loStep)
        ifSteps = makeSteps(self.settings.ifStart, self.settings.ifStop, self.settings.ifStep)
        self.powerMeter.setUnits(Unit.DBM)
        self.powerMeter.setFastMode(False)
        self.warmIFPlate.outputSwitch.setValue(OutputSelect.POWER_METER, LoadSelect.THROUGH, PadSelect.PAD_OUT)
        self.warmIFPlate.inputSwitch.setValue(InputSelect.POL0_USB)
        self.warmIFPlate.yigFilter.setFrequency(self.settings.ifStart)
        self.warmIFPlate.attenuator.setValue(22.0)
        self.__rfSourceOff()

        for freqLO in loSteps:
            if self.stopNow:
                self.finished = True
                self.measurementStatus.setStatusMessage("User stop")
                self.logger.info("User stop")
                return

            self.measurementStatus.setStatusMessage(f"Locking LO at {freqLO:.2f} GHz...")
            success, msg = self.cartAssembly.lockLO(self.loReference, freqLO)
            
            if not success:
                self.logger.error(msg)
            else:
                self.logger.info(msg)

            success = self.cartAssembly.setRecevierBias(freqLO)
            if not success:
                self.logger.error("cartAssembly.setRecevierBias failed. Provide config ID?")
                return
            
            self.measurementStatus.setStatusMessage(f"Setting LO power...")
            success = self.cartAssembly.setAutoLOPower(pol1 = False)
            if not success:
                self.logger.error("cartAssembly.setAutoLOPower failed")

            for freqIF in ifSteps:
                success, msg = self.__checkColdLoad()
                if not success:
                    self.logger.error(msg)
                else:
                    self.logger.info(msg)

                if self.stopNow:
                    self.finished = True                
                    self.logger.info("User stop")
                    self.measurementStatus.setStatusMessage("User stop")
                    return

                success, msg = self.__attenuatorAutoLevel()
                if not success:
                    self.logger.error(msg)
                else:
                    self.logger.info(msg)
                    
                tAmb, tErr = self.tempMonitor.readSingle(self.commonSettings.sensorAmbient)
                now = datetime.now()
                self.rawDataRecords = (
                    NoiseTempRawDatum(
                        fkCartTest = self.keyCartTest,
                        timeStamp = now,
                        FreqLO = freqLO,
                        CenterIF = freqIF,
                        BWIF = 100,
                        Pol = 0,
                        TRF_Hot = tAmb,
                        IF_Attn = self.ifAtten, 
                        TColdLoad = self.commonSettings.tColdEff
                    ),
                    NoiseTempRawDatum(
                        fkCartTest = self.keyCartTest,
                        timeStamp = now,
                        FreqLO = freqLO,
                        CenterIF = freqIF,
                        BWIF = 100,
                        Pol = 1,
                        TRF_Hot = tAmb,
                        IF_Attn = self.ifAtten, 
                        TColdLoad = self.commonSettings.tColdEff
                    )
                )
                    
                if self.doImageReject:
                    success, msg = self.__measureImageReject(freqLO, freqIF)
                    if not success:
                        self.logger.error(msg)
                    else:
                        self.logger.info(msg)
                
                if self.stopNow:
                    self.finished = True                
                    self.logger.info("User stop")
                    self.measurementStatus.setStatusMessage("User stop")
                    return

                if self.doNoiseTemp:
                    success, msg = self.__measureNoiseTemperature(freqLO, freqIF)
                    if not success:
                        self.logger.error(msg)
                    else:
                        self.logger.info(msg)

                if self.stopNow:
                    self.finished = True                
                    self.logger.info("User stop")
                    self.measurementStatus.setStatusMessage("User stop")
                    return

                self.ntRawData.create(self.rawDataRecords[0])
                self.ntRawData.create(self.rawDataRecords[1])
        self.measurementStatus.setStatusMessage("Noise Temperature: Done.")
        self.finished = True

    def __measureImageReject(self, freqLO: float, freqIF: float) -> Tuple[bool, str]:
        self.measurementStatus.setStatusMessage(f"Measure image rejection LO={freqLO:.2f} GHz, IF={freqIF:.2f} GHz...")
        self.chopper.gotoHot()
        self.powerMeter.setUnits(Unit.DBM)
        self.powerMeter.setFastMode(False)
        self.warmIFPlate.yigFilter.setFrequency(freqIF)
        
        for pol in (0, ):

            self.imageRejectHistory = []

            if self.stopNow:
                self.finished = True                
                return True, "User stop"
            
            self.measurementStatus.setStatusMessage(f"Locking RF source at {freqLO + freqIF:.2f} GHz...")
            success, msg = self.rfSrcDevice.lockRF(self.rfReference, freqLO + freqIF, self.commonSettings.sigGenAmplitude)
            if success:
                self.warmIFPlate.inputSwitch.setPolAndSideband(pol, 'USB')
                time.sleep(0.25)                
                success, msg = self.__rfSourceAutoLevel()
                self.rawDataRecords[pol].PwrUSB_SrcUSB = self.powerMeter.read()
                self.warmIFPlate.inputSwitch.setPolAndSideband(pol, 'LSB')
                time.sleep(0.25)                
                self.rawDataRecords[pol].PwrLSB_SrcUSB = self.powerMeter.read()
            if success:
                self.logger.info(msg)
            else:
                self.logger.error(msg)

            if self.stopNow:
                self.finished = True                
                return True, "User stop"      
            
            if success:
                self.measurementStatus.setStatusMessage(f"Locking RF source at {freqLO - freqIF:.2f} GHz...")
                success, msg = self.rfSrcDevice.lockRF(self.rfReference, freqLO - freqIF, self.commonSettings.sigGenAmplitude)
                self.warmIFPlate.inputSwitch.setPolAndSideband(pol, 'LSB')
                time.sleep(0.25)                
                success, msg = self.__rfSourceAutoLevel()
                self.rawDataRecords[pol].PwrLSB_SrcLSB = self.powerMeter.read()
                self.warmIFPlate.inputSwitch.setPolAndSideband(pol, 'USB')
                time.sleep(0.25)                
                self.rawDataRecords[pol].PwrUSB_SrcLSB = self.powerMeter.read()
            if success:
                self.logger.info(msg)
            else:
                self.logger.error(msg)

        self.__rfSourceOff()
        return True, ""

    def __measureNoiseTemperature(self, freqLO: float, freqIF: float) -> Tuple[bool, str]:
        self.measurementStatus.setStatusMessage(f"Measure noise temperature LO={freqLO:.2f} GHz, IF={freqIF:.2f} GHz...")
        self.chopper.spin(self.commonSettings.chopperSpeed)
        self.powerMeter.setUnits(Unit.W)
        self.powerMeter.setFastMode(True)
        self.warmIFPlate.yigFilter.setFrequency(freqIF)
        self.rfSrcDevice.setPAOutput(pol = self.rfSrcDevice.paPol, percent = 0)
        sampleInterval = 1 / self.commonSettings.sampleRate

        for pol in (0, ):
            for sideband in ('USB', 'LSB'):
                if self.stopNow:
                    self.finished = True                
                    return True, "User stop"                       

                self.warmIFPlate.inputSwitch.setPolAndSideband(pol, sideband)
                time.sleep(0.5)
                self.chopperPowerHistory = []
                samplesHot = []
                samplesCold = []
                done = False
                chopperPower = ChopperPowers(input = f"Pol{pol} {sideband}")
                while not done:
                    cycleEnd = time.time() + sampleInterval
                    
                    chopperPower.chopperState = self.chopper.getState()
                    chopperPower.power = self.powerMeter.read()

                    self.chopperPowerHistory.append(copy.copy(chopperPower))                    
                
                    if chopperPower.chopperState == State.OPEN:
                        samplesHot.append(chopperPower.power)
                    elif chopperPower.chopperState == State.CLOSED:
                        samplesCold.append(chopperPower.power)
                
                    if len(samplesHot) >= self.commonSettings.powerMeterConfig.maxS and len(samplesCold) >= self.commonSettings.powerMeterConfig.maxS:                        
                        done = True
                    elif len(samplesHot) >= self.commonSettings.powerMeterConfig.minS and len(samplesCold) >= self.commonSettings.powerMeterConfig.minS:
                        pHotErr = stdev(samplesHot) / sqrt(len(samplesHot))
                        pColdErr = stdev(samplesCold) / sqrt(len(samplesCold))
                        if pHotErr <= self.commonSettings.powerMeterConfig.stdErr and pColdErr <= self.commonSettings.powerMeterConfig.stdErr:
                            done = True
                
                    now = time.time()
                    if now < cycleEnd:
                        time.sleep(cycleEnd - now)

                if sideband == 'USB':
                    self.rawDataRecords[pol].Phot_USB = 10 * log10(mean(samplesHot) * 1000)
                    self.rawDataRecords[pol].Pcold_USB = 10 * log10(mean(samplesCold) * 1000)
                    self.rawDataRecords[pol].Phot_USB_StdErr = pHotErr
                    self.rawDataRecords[pol].Pcold_USB_StdErr = pColdErr
                else:
                    self.rawDataRecords[pol].Phot_LSB = 10 * log10(mean(samplesHot) * 1000)
                    self.rawDataRecords[pol].Pcold_LSB = 10 * log10(mean(samplesCold) * 1000)
                    self.rawDataRecords[pol].Phot_LSB_StdErr = pHotErr
                    self.rawDataRecords[pol].Pcold_LSB_StdErr = pColdErr
        return True, ""

    def __rfSourceAutoLevel(self) -> Tuple[bool, str]:
        if SIMULATE:
            return (True, "")

        setValue = 15 # percent
        maxIter = 25
        
        controller = BinarySearchController(
            outputRange = [15, 100], 
            initialStepPercent = 10, 
            initialOutput = setValue, 
            setPoint = self.commonSettings.targetSidebandPower,
            tolerance = 1,
            maxIter = maxIter)
        
        self.rfSrcDevice.setPAOutput(self.rfSrcDevice.paPol, setValue) 
        amp = self.powerMeter.read()
        done = error = False
        msg = ""
        iter = 0

        if not amp:
            error = True
        while not done and not error: 
            iter += 1
            if iter >= maxIter or setValue >= 100:
                error = True
                msg = f"__rfSourceAutoLevel: iter={iter} maxIter={maxIter} setValue={setValue}%"
            elif (self.commonSettings.targetSidebandPower - 1) < amp < (self.commonSettings.targetSidebandPower + 1):
                done = True
                msg = f"__rfSourceAutoLevel: success iter={iter} amp={amp:.1f} dBm"
            else:
                controller.process(amp)
                setValue = controller.output
                self.rfSrcDevice.setPAOutput(self.rfSrcDevice.paPol, setValue)
                time.sleep(0.2)
                amp = self.powerMeter.read()
                if amp is None:
                    error = True
                    msg = f"__rfSourceAutoLevel: powerMeter.read error at iter={iter}."
                self.logger.info(f"__rfSourceAutoLevel: iter={iter} amp={amp:.1f} dBm")

        if error:
            self.logger.error(msg)
        else:
            self.logger.info(msg)
        return (not error, msg)

    def __attenuatorAutoLevel(self):
        self.measurementStatus.setStatusMessage("Setting attenuator...")
        self.chopper.gotoHot()
        self.powerMeter.setUnits(Unit.DBM)
        self.warmIFPlate.inputSwitch.setValue(InputSelect.POL0_USB)

        # treating (max - atten) as gain because BinarySearchController wants the input to go up when the output does.
        setValue = 100 - self.ifAtten
        maxIter = 25
        
        controller = BinarySearchController(
            outputRange = [0, 100], 
            initialStepPercent = 10, 
            initialOutput = setValue, 
            setPoint = self.commonSettings.targetPHot,
            tolerance = 0.5,
            maxIter = maxIter)

        self.warmIFPlate.attenuator.setValue(100 - setValue)
        amp = self.powerMeter.read()

        done = error = False
        msg = ""
        iter = 0

        if not amp:
            error = True
        while not done and not error: 
            iter += 1
            if iter >= maxIter:
                done = True
                msg = f"__attenuatorAutoLevel: iter={iter} maxIter={maxIter} setValue={100 - setValue} dB"
            elif controller.isComplete():
                done = True
                msg = f"__attenuatorAutoLevel: success iter={iter} amp={amp:.1f} dBm setValue={100 - setValue} dB"
            else:
                controller.process(amp)
                setValue = int(round(controller.output))
                self.warmIFPlate.attenuator.setValue(100 - setValue)
                time.sleep(0.25)
                amp = self.powerMeter.read()
                if amp is None:
                    error = True
                    msg = f"__attenuatorAutoLevel: powerMeter.read error at iter={iter}."
                self.logger.info(f"__attenuatorAutoLevel: iter={iter} amp={amp:.1f} dBm setValue={100 - setValue} dB")

        if error:
            self.logger.error(msg)
        else:
            self.logger.info(msg)
        self.ifAtten = 100 - setValue
        return (not error, msg)

    def __rfSourceOff(self) -> Tuple[bool, str]:
        self.rfSrcDevice.setPAOutput(pol = self.rfSrcDevice.paPol, percent = 0)
        return (True, "")

    def __checkColdLoad(self) -> Tuple[bool, str]:
        shouldPause, msg = self.coldLoadController.shouldPause(enablePause = self.commonSettings.pauseForColdLoad)
        while shouldPause and not self.stopNow:
            self.measurementStatus.setStatusMessage("Cold load " + msg)
            time.sleep(10)
            shouldPause, msg = self.coldLoadController.shouldPause(enablePause = self.commonSettings.pauseForColdLoad)
        
        if self.stopNow:
            self.finished = True                
            return True, "User stop"

        return True, msg
    
