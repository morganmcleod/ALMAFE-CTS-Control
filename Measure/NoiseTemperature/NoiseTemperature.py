from CTSDevices.WarmIFPlate.WarmIFPlate import WarmIFPlate
from CTSDevices.WarmIFPlate.InputSwitch import InputSelect
from CTSDevices.PowerMeter.KeysightE441X import PowerMeter, Unit
from CTSDevices.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from CTSDevices.Chopper.Band6Chopper import Chopper, State
from CTSDevices.SignalGenerator.Keysight_PSG_MXG import SignalGenerator
from CTSDevices.FEMC.CartAssembly import CartAssembly
from CTSDevices.Common.BinarySearchController import BinarySearchController
from DBBand6Cart.NoiseTempRawData import NoiseTempRawData
from AMB.LODevice import LODevice
from app.database.CTSDB import CTSDB
from .schemas import ImageRejectPowers, NoiseTempPowers
from ..Shared.makeSteps import makeSteps
from ..Shared.MeasurementStatus import MeasurementStatus

from DebugOptions import *

import concurrent.futures
import logging
import time
from typing import Tuple
import numpy as np

class NoiseTemperature():

    def __init__(self,
            loReference: SignalGenerator,
            rfReference: SignalGenerator,
            cartAssembly: CartAssembly,
            rfSrcDevice: LODevice,
            warmIFPlate: WarmIFPlate,
            powerMeter: PowerMeter,
            tempMonitor: TemperatureMonitor,
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
        self.chopper = chopper
        self.measurementStatus = measurementStatus
        self.ntRawData = NoiseTempRawData(driver = CTSDB())
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers = 1)
        self.__reset()        

    def __reset(self):
        self.settings = None
        self.commonSettings = None
        self.keyCartTest = 0
        self.stopNow = False
        self.finished = False
        self.rawData = []

    def start(self, doImageReject: bool):
        self.doNoiseTemp = True
        self.doImageReject = doImageReject
        self.stopNow = False
        self.finished = False
        self.futures = []
        self.futures.append(self.executor.submit(self.__run))

    def stop(self):
        self.stopNow = True

    def isMeasuring(self):
        return not self.finished

    def __run(self) -> None:
        self.chopper.stop()
        loSteps = makeSteps(self.settings.loStart, self.settings.loStop, self.settings.loStep)
        ifSteps = makeSteps(self.settings.ifStart, self.settings.ifStop, self.settings.ifStep)

        for freqLO in loSteps:
            if self.stopNow:
                self.finished = True
                self.logger.info("User stop")
                return

            success, msg = lockLO(self.loReference, freqLO)
            if not success:
                self.logger.error(msg)
            else:
                self.logger.info(msg)

            success = self.cartAssembly.setRecevierBias(freqLO)
            if not success:
                self.logger.error("cartAssembly.setRecevierBias failed. Provide config ID?")
                return
            
            success = cartAssembly.setAutoLOPower()
            if not success:
                self.logger.error("cartAssembly.setAutoLOPower failed")

            for freqIF in ifSteps:
                if self.stopNow:
                    self.finished = True                
                    self.logger.info("User stop")
                    return

                if self.doImageReject:
                    success, msg = self.__measureImageReject(freqLO, freqIF)
                    if not success:
                        self.logger.error(msg)
                    else:
                        self.logger.info(msg)

                if self.doNoiseTemp:
                    success, msg = self.__measureNoiseTemperature(freqLO, freqIF)
                    if not success:
                        self.logger.error(msg)
                    else:
                        self.logger.info(msg)

    def __measureImageReject(self, freqLO: float, freqIF: float) -> Tuple[bool, str]:
        self.chopper.gotoHot()
        self.powerMeter.setUnits(Unit.DBM)
        self.powerMeter.setFastMode(False)
        self.warmIFPlate.yigFilter.setFrequency(freqIF)
        
        for pol in (0, 1):
            irPowers = ImageRejectPowers(pol = pol)

            if self.stopNow:
                self.finished = True                
                return True, "User stop"      
            
            success, msg = lockRF(self.rfReference, self.rfSrcDevice, freqLO + freqIF)
            if success:
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
                self.finished = True                
                return True, "User stop"      
            
            if success:
                success, msg = lockRF(self.rfReference, self.rfSrcDevice, freqLO + freqIF)
                self.warmIFPlate.inputSwitch.setValue(InputSelect.POL0_LSB if pol == 0 else InputSelect.POL1_LSB)
                success, msg = self.__rfSourceAutoLevel()
                irPowers.PwrLSB_SrcLSB = self.powerMeter.read()
                self.warmIFPlate.inputSwitch.setValue(InputSelect.POL0_USB if pol == 0 else InputSelect.POL1_USB)
                irPowers.PwrUSB_SrcLSB = self.powerMeter.read()
            if success:
                self.logger.info(msg)
            else:
                self.logger.error(msg)

            msg = f"Image Rejection LO:{freqLO}, IF:{freqIF}, {irPowers.getText()}"
            return True, msg

    def __measureNoiseTemperature(self, freqLO: float, freqIF: float) -> Tuple[bool, str]:
        self.chopper.spin(self.settings.chopperSpeed)
        self.powerMeter.setUnits(Unit.DBM)
        self.powerMeter.setFastMode(True)
        self.warmIFPlate.yigFilter.setFrequency(freqIF)
        self.rfSrcDevice.setPAOutput(pol = self.rfSrcDevice.paPol, percent = 0)
        sampleInterval = 1 / self.commonSettings.sampleRate

        for pol in 0, 1:
            ntPowers = NoiseTempPowers(pol = pol)
            for ifSelect in (InputSelect.POL0_USB, InputSelect.POL0_LSB) if pol == 0 else (InputSelect.POL1_USB, InputSelect.POL1_LSB):
                if self.stopNow:
                    self.finished = True                
                    return True, "User stop"                       

                self.warmIFPlate.inputSwitch.setValue(ifSelect)
                samplesHot = np.array(dtype = np.float_)
                samplesCold = np.array(dtype = np.float_)
                done = False
                while not done:
                    cycleStart = time.time()
                    cycleEnd = cycleStart + sampleInterval
                    state = self.chopper.getState()
                    power = self.powerMeter.read()
                    if state == State.OPEN:
                        np.append(samplesHot, (10 ** (power / 10)) / 1000)
                    elif state == State.CLOSED:
                        np.append(samplesCold, (10 ** (power / 10)) / 1000)
                    if samplesHot.size >= self.commonSettings.powerMeterConfig.maxS:
                        done = True
                    if samplesHot.size >= self.commonSettings.powerMeterConfig.minS:
                        pHotErr = np.std(samplesHot) / np.sqrt(max(1, samplesHot.size))
                        pColdErr = np.std(samplesCold) / np.sqrt(max(1, samplesCold.size))
                        if pHotErr <= self.commonSettings.powerMeterConfig.stdErr and pColdErr <= self.commonSettings.powerMeterConfig.stdErr:
                            done = True
                    now = time.time()
                    if now < cycleEnd:
                        time.sleep(cycleEnd - now)

                if ifSelect in (InputSelect.POL0_USB, InputSelect.POL1_USB):
                    ntPowers.Phot_USB = 10 * np.log10(np.mean(samplesHot) * 1000)
                    ntPowers.Pcold_USB = 10 * np.log10(np.mean(samplesCold) * 1000)
                    ntPowers.Phot_USB_StdErr = pHotErr
                    ntPowers.Pcold_USB_StdErr = pColdErr
                else:
                    ntPowers.Phot_LSB = 10 * np.log10(np.mean(samplesHot) * 1000)
                    ntPowers.Pcold_LSB = 10 * np.log10(np.mean(samplesCold) * 1000)
                    ntPowers.Phot_LSB_StdErr = pHotErr
                    ntPowers.Pcold_LSB_StdErr = pColdErr

                msg = f"Noise Temperature LO:{freqLO}, IF:{freqIF}, {ntPowers.getText()}"
                return True, msg

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
