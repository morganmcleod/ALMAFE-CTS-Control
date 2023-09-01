from CTSDevices.WarmIFPlate.WarmIFPlate import WarmIFPlate
from CTSDevices.WarmIFPlate.InputSwitch import InputSelect, InputSwitch
from CTSDevices.PowerMeter.KeysightE441X import PowerMeter, Unit
from CTSDevices.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from CTSDevices.Chopper.Band6Chopper import Chopper, State
from CTSDevices.SignalGenerator.Keysight_PSG_MXG import SignalGenerator
from CTSDevices.Cartridge.CartAssembly import CartAssembly
from CTSDevices.Common.BinarySearchController import BinarySearchController
from DBBand6Cart.schemas.WarmIFNoise import DUT_Types
from DBBand6Cart.NoiseTempRawData import NoiseTempRawData
from AMB.LODevice import LODevice
from app.database.CTSDB import CTSDB
from .schemas import NoiseTempSettings, ImageRejectSettings, ImageRejectPowers, NoiseTempPowers

from DebugOptions import *

import logging
import time
from typing import Tuple
from statistics import mean, stdev
from math import sqrt

class MeasureNoiseTemperature():

    def __init__(self,
            loReference: SignalGenerator,
            rfReference: SignalGenerator,
            cartAssembly: CartAssembly,
            rfSrcDevice: LODevice,
            warmIFPlate: WarmIFPlate,
            powerMeter: PowerMeter,
            tempMonitor: TemperatureMonitor,
            chopper: Chopper,
            ntSettings: NoiseTempSettings,
            irSettings: ImageRejectSettings):
        
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.loReference = loReference
        self.rfReference = rfReference
        self.cartAssembly = cartAssembly
        self.rfSrcDevice = rfSrcDevice        
        self.warmIFPlate = warmIFPlate
        self.powerMeter = powerMeter
        self.tempMonitor = tempMonitor
        self.chopper = chopper
        self.ntSettings = ntSettings
        self.irSettings = irSettings
        self.ntRawData = NoiseTempRawData(driver = CTSDB())
        self.keyCartTest = 0
        self.stopNow = False
        self.finished = False

    def start(self):
        self.stopNow = False
        self.finished = False
        self.__run()
        self.finished = True

    def stop(self):
        self.stopNow = True

    def finished(self):
        return self.finished

    def __run(self):
        
        
        self.chopper.stop()
        loSteps = [self.settings.loStart + i * self.settings.loStep for i in range(int((self.settings.loStop - self.settings.loStart) / self.settings.loStep + 1))]
        ifSteps = [self.settings.ifStart + i * self.settings.ifStep for i in range(int((self.settings.ifStop - self.settings.ifStart) / self.settings.ifStep + 1))]

        for freqLO in loSteps:
            if self.stopNow:
                self.logger.info("User stop")
                return

            success, msg = self.__lockLO(freqLO)
            if not success:
                self.logger.error(msg)
            else:
                self.logger.info(msg)

            if success:
                for freqIF in ifSteps:
                    if self.stopNow:
                        self.logger.info("User stop")
                        return

                    if self.irSettings and self.irSettings.enable:
                        self.chopper.gotoHot()
                        self.powerMeter.setUnits(Unit.DBM)
                        self.powerMeter.setFastMode(False)
                        self.warmIFPlate.yigFilter.setFrequency(freqIF)
                        self.__lockRF(freqIF)

                        for pol in 0, 1:
                            irPowers = ImageRejectPowers(pol = pol)

                            if self.stopNow:
                                self.logger.info("User stop")
                                return
    
                            self.warmIFPlate.inputSwitch.setValue(InputSelect.POL0_USB if pol == 0 else InputSelect.POL1_USB)
                            success, msg = self.__rfSourceAutoLevel()
                            irPowers.PwrUSB_SrcUSB = self.powerMeter.read()
                            self.warmIFPlate.inputSwitch.setValue(InputSelect.POL0_LSB if pol == 0 else InputSelect.POL1_LSB)
                            irPowers.PwrLSB_SrcUSB = self.powerMeter.read()
                            if success:
                                self.logger.info(msg)
                            else:
                                self.logger.error(msg)

                            if self.stopNow:
                                self.logger.info("User stop")
                                return

                            self.warmIFPlate.inputSwitch.setValue(InputSelect.POL0_LSB if pol == 0 else InputSelect.POL1_LSB)
                            success, msg = self.__rfSourceAutoLevel()
                            irPowers.PwrLSB_SrcLSB = self.powerMeter.read()
                            self.warmIFPlate.inputSwitch.setValue(InputSelect.POL0_USB if pol == 0 else InputSelect.POL1_USB)
                            irPowers.PwrUSB_SrcLSB = self.powerMeter.read()
                            if success:
                                self.logger.info(msg)
                            else:
                                self.logger.error(msg)

                            self.logger.info(f"Image Rejection LO:{freqLO}, IF:{freqIF}, {irPowers.getText()}")

                    if self.ntSettings and self.ntSettings.enable:
                        self.chopper.spin(self.ntSettings.chopperSpeed)
                        self.powerMeter.setUnits(Unit.DBM)
                        self.powerMeter.setFastMode(True)
                        self.warmIFPlate.yigFilter.setFrequency(freqIF)
                        self.rfSrcDevice.setPAOutput(pol = self.rfSrcDevice.paPol, percent = 0)
                        sampleInterval = 1 / self.ntSettings.sampleRate

                        for pol in 0, 1:
                            ntPowers = NoiseTempPowers(pol = pol)
                            for ifSelect in (InputSelect.POL0_USB, InputSelect.POL0_LSB) if pol == 0 else (InputSelect.POL1_USB, InputSelect.POL1_LSB):
                                if self.stopNow:
                                    self.logger.info("User stop")
                                    return                        

                                self.warmIFPlate.inputSwitch.setValue(ifSelect)
                                samplesHot = []
                                samplesCold = []
                                done = False
                                while not done:
                                    cycleStart = time.time()
                                    cycleEnd = cycleStart + sampleInterval
                                    state = self.chopper.getState()
                                    power = self.powerMeter.read()
                                    if state == State.OPEN:
                                        samplesHot.append(power)
                                    elif state == State.CLOSED:
                                        samplesCold.append(power)
                                    if len(samplesHot) >= self.ntSettings.powerMeterConfig.maxS:
                                        done = True
                                    if len(samplesHot) >= self.ntSettings.powerMeterConfig.minS:
                                        pHotErr = stdev(samplesHot) / sqrt(min(1, len(samplesHot)))
                                        pColdErr = stdev(samplesCold) / sqrt(min(1, len(samplesCold)))
                                        if pHotErr <= self.ntSettings.powerMeterConfig.stdErr and pColdErr <= self.ntSettings.powerMeterConfig.stdErr:
                                            done = True
                                    now = time.time()
                                    if now < cycleEnd:
                                        time.sleep(cycleEnd - now)

                                if ifSelect in (InputSelect.POL0_USB, InputSelect.POL1_USB):
                                    ntPowers.Phot_USB = mean(samplesHot)
                                    ntPowers.Pcold_USB = mean(samplesCold)
                                    ntPowers.Phot_USB_StdErr = pHotErr
                                    ntPowers.Pcold_USB_StdErr = pColdErr
                                else:
                                    ntPowers.Phot_LSB = mean(samplesHot)
                                    ntPowers.Pcold_LSB = mean(samplesCold)
                                    ntPowers.Phot_LSB_StdErr = pHotErr
                                    ntPowers.Pcold_LSB_StdErr = pColdErr

                                self.logger.info(f"Noise Temperature LO:{freqLO}, IF:{freqIF}, {ntPowers.getText()}")

    def __lockLO(self, freqLO: float) -> Tuple[bool, str]:
        self.cartAssembly.loDevice.selectLockSideband(self.cartAssembly.loDevice.LOCK_ABOVE_REF)
        wcaFreq, ytoFreq, ytoCourse = self.cartAssembly.loDevice.setLOFrequency(freqLO)
        pllConfig = self.cartAssembly.loDevice.getPLLConfig()
        self.loReference.setFrequency((freqLO / pllConfig['coldMult'] - 0.020) / pllConfig['warmMult'])
        self.loReference.setAmplitude(12.0)
        self.loReference.setRFOutput(True)
        if not SIMULATE:
            wcaFreq, ytoFreq, ytoCourse = self.cartAssembly.loDevice.lockPLL()
        return (True, f"__lockLO: wca={wcaFreq}, yto={ytoFreq}, courseTune={ytoCourse}")
    
    def __lockRF(self, freqRF: float) -> Tuple[bool, str]:
        self.rfSrcDevice.selectLockSideband(self.rfSrcDevice.LOCK_ABOVE_REF)
        wcaFreq, ytoFreq, ytoCourse = self.rfSrcDevice.setLOFrequency(freqRF)
        pllConfig = self.rfSrcDevice.getPLLConfig()
        self.rfReference.setFrequency((freqRF / pllConfig['coldMult'] - 0.020) / pllConfig['warmMult'])
        self.rfReference.setAmplitude(16.0)
        self.rfReference.setRFOutput(True)
        if not SIMULATE:
            wcaFreq, ytoFreq, ytoCourse = self.rfSrcDevice.lockPLL()
        return (True, f"__lockRF: wca={wcaFreq}, yto={ytoFreq}, courseTune={ytoCourse}")

    def __rfSourceAutoLevel(self) -> Tuple[bool, str]:
        if SIMULATE:
            return (True, "")

        setValue = 15 # percent
        maxIter = 25
        
        controller = BinarySearchController(
            outputRange = [15, 100], 
            initialStep = 0.1, 
            initialOutput = setValue, 
            setPoint = self.irSettings.targetSidebandPower,
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
            elif (self.irSettings.targetSidebandPower - 1) < amp < (self.irSettings.targetSidebandPower + 1):
                done = True
                msg = f"__rfSourceAutoLevel: success iter={iter} amp={amp:.1f} dBM"
            else:
                controller.process(amp)
                setValue = controller.output
                self.rfSrcDevice.setPAOutput(self.rfSrcDevice.paPol, setValue)
                time.sleep(0.2)
                amp = self.powerMeter.read()
                if amp is None:
                    error = True
                    msg = f"__rfSourceAutoLevel: powerMeter.read error at iter={iter}."
                self.logger.info(f"__rfSourceAutoLevel: iter={iter} amp={amp:.1f} dBM")

        if error:
            self.logger.error(msg)
        else:
            self.logger.info(msg)
        return (not error, msg)
