from CTSDevices.MotorControl.schemas import MoveStatus, Position
from CTSDevices.MotorControl.MCInterface import MCInterface
from CTSDevices.PNA.schemas import MeasConfig, PowerConfig, MeasType, SweepType, Format, SweepGenType, TriggerSource
from CTSDevices.PNA.PNAInterface import PNAInterface
from CTSDevices.PNA.AgilentPNA import DEFAULT_CONFIG, FAST_CONFIG, DEFAULT_POWER_CONFIG
from CTSDevices.SignalGenerator.Keysight_PSG_MXG import SignalGenerator
from CTSDevices.WarmIFPlate.InputSwitch import InputSelect
from CTSDevices.WarmIFPlate.OutputSwitch import PadSelect, LoadSelect, OutputSelect
from AMB.LODevice import LODevice
from CTSDevices.Cartridge.CartAssembly import CartAssembly
from CTSDevices.Common.BinarySearchController import BinarySearchController
from .schemas import MeasurementSpec, ScanList, ScanListItem, ScanStatus, SubScan, Raster, Rasters
import time
from datetime import datetime
import concurrent.futures
from typing import Tuple
import copy
import logging

class BeamScanner():

    XY_SPEED_POSITIONING = 40       # mm/sec
    XY_SPEED_SCANNING = 20          # mm/sec
    POL_SPEED = 20                  # deg/sec

    def __init__(self, 
        motorController:MCInterface, 
        pna:PNAInterface, 
        loReference:SignalGenerator, 
        cartAssembly:CartAssembly,
        rfSrcDevice:LODevice,
        warmIFPlate:object):
        
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.mc = motorController
        self.pna = pna
        self.loReference = loReference
        self.rfReference = None     # normally we don't use the RF source reference synth.  Set this to do so for debugging.
        self.cartAssembly = cartAssembly
        self.rfSrcDevice = rfSrcDevice
        self.warmIFPlate = warmIFPlate
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers = 3)
        self.measurementSpec = MeasurementSpec()
        self.scanList = ScanList()
        self.futures = None
        self.keyCartTest = 0
        self.__reset()
        
    def __reset(self):
        self.scanStatus = ScanStatus(key = self.keyCartTest)
        self.__resetRasters()

    def getRasters(self):
        if self.nextRaster == -1:
            self.nextRaster = 0
            return Rasters()
        elif self.nextRaster < len(self.rasters):
            response = Rasters(startIndex = self.nextRaster, rasters = self.rasters[self.nextRaster:])
            self.nextRaster = len(self.rasters)
            return response
        else:
            return None

    def start(self):
        self.stopNow = False
        self.scanStatus = ScanStatus()
        self.futures = []
        self.futures.append(self.executor.submit(self.__runAllScans))

    def stop(self):
        self.stopNow = True
        self.mc.stopMove()
        if self.futures:
            concurrent.futures.wait(self.futures)
        self.logger.info("BeamScanner: stopped")

    def __runAllScans(self):
        success, msg = self.__resetRasters();
        if not success:
            return
        success, msg = self.__resetPNA()
        if not success:
            return

        self.mc.setTriggerInterval(self.measurementSpec.resolution)

        self.scanList.updateIndex()
        for scan in self.scanList.items:
            if scan.enable:
                self.__reset()
                self.scanStatus.activeScan = scan.index
                self.logger.info(scan.getText())
                scan.makeSubScans()
                for subScan in scan.subScans:
                    if self.stopNow:
                        self.__abortScan("User Stop")
                        return
                    self.logger.info(subScan.getText())
                    self.scanStatus.message = "Started: " + subScan.getText()
                    self.scanStatus.activeSubScan = subScan.getText()
                    success, msg = self.__runOneScan(scan, subScan)
                    self.logger.info(f"{success}:{msg}")
                    self.scanStatus.activeSubScan = None
                    if success:
                        self.scanStatus.message = "Scan complete"
                    else:
                        self.scanStatus.message = "Error: " + msg
                self.scanStatus.activeScan = None
        self.scanStatus.scanComplete = True
        self.scanStatus.measurementComplete = True

    def __runOneScan(self, scan:ScanListItem, subScan:SubScan) -> Tuple[bool, str]:
        try:
            success, msg = self.__resetRasters()
            if success:
                success, msg = self.__configureIfProcessor(scan, subScan)
            if success:
                success, msg = self.__rfSourceOff()
            if success:
                success, msg = self.__lockLO(scan, subScan)
            if success:
                success, msg = self.__setReceiverBias(scan, subScan)
            if success:
                success, msg = self.__lockRF(scan, subScan)
            if success:
                success, msg = self.__moveToBeamCenter(scan, subScan)
            if success:
                success, msg = self.__rfSourceAutoLevel(scan, subScan)
            
            if not success:
                return (success, msg)

            self.__selectIFInput(isUSB = scan.RF > scan.LO, pol = subScan.getScanPol())

            lastCenterPwrTime = None
            rasterIndex = 0;
            # loop on y axis:
            for yPos in self.measurementSpec.makeYAxisList():

                # check for User Stop signal
                if self.stopNow:
                    self.__abortScan("User Stop")
                    return False

                # time to record the beam center power?
                if not lastCenterPwrTime or (time.time() - lastCenterPwrTime) > self.measurementSpec.centersInterval:
                    lastCenterPwrTime = time.time()

                    success, msg = self.__measureCenterPower(scan, subScan, scanComplete = False)
                    if not success:
                        self.__abortScan(msg)
                        return (success, msg)

                # check for User Stop signal
                if self.stopNow:
                    self.__abortScan("User Stop")
                    return False

                # go to start of this raster:
                nextPos = Position(x = self.measurementSpec.scanStart.x, y = yPos, pol = self.measurementSpec.scanAngles[subScan.pol])
                self.raster = Raster(
                    rasterIndex = rasterIndex, 
                    startPos = nextPos, 
                    xStep = self.measurementSpec.resolution
                )
                success, msg = self.__moveScanner(nextPos, withTrigger = False)
                if not success:
                    self.__abortScan(msg)
                    return (success, msg)

                # calculate next position and move timeout:
                nextPos = Position(x = self.measurementSpec.scanEnd.x, y = yPos, pol = self.measurementSpec.scanAngles[subScan.pol])
                self.mc.setXYSpeed(self.XY_SPEED_SCANNING)
                moveTimeout = self.mc.estimateMoveTime(self.mc.getPosition(), nextPos)

                # configure external triggering:
                success, msg = self.__configurePNARaster(scan, subScan, yPos, moveTimeout)
                if not success:
                    self.__abortScan(msg)
                    return (success, msg)

                # start the move:
                success, msg = self.__moveScanner(nextPos, withTrigger = True, moveTimeout = moveTimeout)
                if not success:
                    self.__abortScan(msg)
                    return (success, msg)
                
                # get the PNA trace data:
                success, msg = self.__getPNARaster(scan, subScan, y = yPos)
                if not success:
                    self.__abortScan(msg)
                    return (success, msg)

            # record the beam center power a final time:
            success, msg = self.__measureCenterPower(scan, subScan, scanComplete = True)
            if not success:
                self.__abortScan(msg)
                return (success, msg)
            else:
                return (True, "__runOneScan complete")
        except Exception as e:
            self.logger.exception(e)
            return (False, "__runOneScan Exception: " + str(e))

    def __moveScanner(self, nextPos:Position, withTrigger:bool, moveTimeout = None) -> Tuple[bool, str]:
        self.mc.setXYSpeed(self.XY_SPEED_SCANNING if withTrigger else self.XY_SPEED_POSITIONING)
        self.mc.setPolSpeed(self.POL_SPEED)
        if not moveTimeout:
            moveTimeout = self.mc.estimateMoveTime(self.mc.getPosition(), nextPos)
        self.logger.debug(f"move to {nextPos.getText()} trigger={withTrigger} moveTimeout={moveTimeout:.1f}")
        self.mc.setNextPos(nextPos)
        self.mc.startMove(withTrigger, moveTimeout)
        moveStatus = self.mc.waitForMove()
        self.mc.stopMove()
        if self.stopNow:
            return (False, "__moveScanner: User Stop")
        else:
            return (not moveStatus.isError(), "__moveScanner: " + moveStatus.getText())

    def __measureCenterPower(self, scan:ScanListItem, subScan:SubScan, scanComplete:bool = False) -> Tuple[bool, str]:
        success, msg = self.__moveToBeamCenter(scan, subScan)
        if not success:
            return (success, msg)
        self.pna.setMeasConfig(FAST_CONFIG)
        self.__selectIFInput(isUSB = scan.RF > scan.LO, pol = subScan.pol)

        amp, phase = self.pna.getAmpPhase()        
        self.scanStatus.amplitude = amp if amp else -999
        self.scanStatus.phase = phase if phase else 0
        self.scanStatus.timeStamp = datetime.now()
        self.scanStatus.scanComplete = scanComplete
        self.__selectIFInput(isUSB = scan.RF > scan.LO, pol = subScan.getScanPol())
        msg = f"__measureCenterPower: {self.scanStatus.getCenterPowerText()}"
        self.logger.info(msg)
        return (True, msg)

    def __abortScan(self, msg) -> Tuple[bool, str]:
        self.logger.info(msg)
        self.scanStatus.activeScan = None
        self.scanStatus.activeSubScan = None
        self.scanStatus.message = msg
        self.scanStatus.error = True
        return (False, msg)

    def __resetPNA(self) -> Tuple[bool, str]:
        self.pna.reset()
        self.pna.workaroundPhaseLockLost()
        self.pnaConfig = copy.copy(DEFAULT_CONFIG)        
        self.pnaConfig.triggerSource = TriggerSource.EXTERNAL
        self.pna.setMeasConfig(self.pnaConfig)
        self.pna.setPowerConfig(DEFAULT_POWER_CONFIG)
        code, msg = self.pna.errorQuery()
        return (code == 0, "__resetPNA: " + msg)

    def __resetRasters(self) -> Tuple[bool, str]:
        self.rasters = []
        self.nextRaster = -1
        return (True, "")

    def __configureIfProcessor(self, scan:ScanListItem, subScan:SubScan) -> Tuple[bool, str]:
        self.__selectIFInput(isUSB = scan.RF > scan.LO, pol = subScan.pol)
        self.warmIFPlate.outputSwitch.setValue(OutputSelect.SQUARE_LAW, LoadSelect.THROUGH, PadSelect.PAD_OUT)
        self.warmIFPlate.yigFilter.setFrequency(abs(scan.RF - scan.LO))
        self.warmIFPlate.attenuator.setValue(22)   # TODO:  move into MeasConfig?
        return (True, "")
    
    def __selectIFInput(self, isUSB: bool, pol: int):
        if isUSB:
            if pol == 0:
                position = InputSelect.POL0_USB
            else:
                position = InputSelect.POL1_USB
        else:
            if pol == 0:
                position = InputSelect.POL0_LSB
            else:
                position = InputSelect.POL1_LSB
        self.warmIFPlate.inputSwitch.setValue(position)

    def __rfSourceOff(self) -> Tuple[bool, str]:
        self.rfSrcDevice.setPAOutput(pol = self.rfSrcDevice.paPol, percent = 0)
        return (True, "")

    def __lockLO(self, scan:ScanListItem, subScan:SubScan) -> Tuple[bool, str]:
        self.cartAssembly.loDevice.selectLockSideband(self.cartAssembly.loDevice.LOCK_ABOVE_REF)
        wcaFreq, ytoFreq, ytoCourse = self.cartAssembly.loDevice.setLOFrequency(scan.LO)
        if wcaFreq > 0:
            pllConfig = self.cartAssembly.loDevice.getPLLConfig()
            self.loReference.setFrequency((scan.LO / pllConfig['coldMult'] - 0.020) / pllConfig['warmMult'])
            self.loReference.setAmplitude(12.0)
            self.loReference.setRFOutput(True)
            wcaFreq, ytoFreq, ytoCourse = self.cartAssembly.loDevice.lockPLL()
        msg = f"__lockLO: wca={wcaFreq}, yto={ytoFreq}, courseTune={ytoCourse}"
        return (wcaFreq != 0, msg)

    def __setReceiverBias(self, scan:ScanListItem, subScan:SubScan) -> Tuple[bool, str]:
        if self.cartAssembly.setRecevierBias(scan.LO):
            ret0 = self.cartAssembly.setAutoLOPower(0)
            ret1 = self.cartAssembly.setAutoLOPower(1)
            if ret0 and ret1:
                return (True, "")
            else:
                return (False, f"cartAssembly.setAutoLOPower failed: pol0:{ret0} pol1:{ret1}")
        else:
            return (False, "cartAssembly.setRecevierBias failed.  Provide config ID?")

    def __lockRF(self, scan:ScanListItem, subScan:SubScan) -> Tuple[bool, str]:
        self.rfSrcDevice.selectLockSideband(self.rfSrcDevice.LOCK_ABOVE_REF)
        wcaFreq, ytoFreq, ytoCourse = self.rfSrcDevice.setLOFrequency(scan.RF)
        if wcaFreq > 0:
            if self.rfReference:
                # for debug only.  Normally the RF ref synth is not used for beam patterns:
                pllConfig = self.rfSrcDevice.getPLLConfig()
                self.rfReference.setFrequency((scan.RF / pllConfig['coldMult'] - 0.020) / pllConfig['warmMult'])
                self.rfReference.setAmplitude(16.0)
                self.rfReference.setRFOutput(True)
            wcaFreq, ytoFreq, ytoCourse = self.rfSrcDevice.lockPLL()
        msg = f"__lockRF: wca={wcaFreq}, yto={ytoFreq}, courseTune={ytoCourse}"
        return (wcaFreq != 0, msg)

    def __moveToBeamCenter(self, scan:ScanListItem, subScan:SubScan) -> Tuple[bool, str]:
        self.measurementSpec.beamCenter.pol = self.measurementSpec.levelAngles[subScan.pol]
        success, msg = self.__moveScanner(self.measurementSpec.beamCenter, withTrigger = False)
        return (success, "__moveToBeamCenter: " + msg)

    def __rfSourceAutoLevel(self, scan:ScanListItem, subScan:SubScan) -> Tuple[bool, str]:
        self.pna.setMeasConfig(FAST_CONFIG)

        setValue = 15 # percent
        maxIter = 25
        
        controller = BinarySearchController(
            outputRange = [15, 100], 
            initialStep = 0.1, 
            initialOutput = setValue, 
            setPoint = self.measurementSpec.targetLevel,
            tolerance = 1,
            maxIter = maxIter)
        
        self.rfSrcDevice.setPAOutput(self.rfSrcDevice.paPol, setValue) 
        amp, _ = self.pna.getAmpPhase()
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
            elif (self.measurementSpec.targetLevel - 1) < amp < (self.measurementSpec.targetLevel + 1):
                done = True
                msg = f"__rfSourceAutoLevel: success iter={iter} amp={amp:.1f} dB"
            else:
                controller.process(amp)
                setValue = controller.output
                self.rfSrcDevice.setPAOutput(self.rfSrcDevice.paPol, setValue)
                time.sleep(0.2)
                amp, _ = self.pna.getAmpPhase()
                if amp is None:
                    error = True
                    msg = f"__rfSourceAutoLevel: getAmpPhase error at iter={iter}."
                self.logger.info(f"__rfSourceAutoLevel: iter={iter} amp={amp:.1f} dB")

        self.pna.setMeasConfig(DEFAULT_CONFIG)
        if error:
            self.logger.error(msg)
        else:
            self.logger.info(msg)
        return (not error, msg)

    def __configurePNARaster(self, scan:ScanListItem, subScan:SubScan, yPos:float, moveTimeout:float) -> Tuple[bool, str]:
        # add 10sec to timeout to account for accel/decel
        self.pnaConfig.timeout_sec = moveTimeout + 10
        self.pnaConfig.sweepPoints = self.measurementSpec.numScanPoints()
        self.pna.setMeasConfig(self.pnaConfig)
        return (True, "")

    def __getPNARaster(self, scan:ScanListItem, subScan:SubScan, y:float = 0) -> Tuple[bool, str]:
        amp, phase = self.pna.getTrace(y = y)
        if amp and phase:
            self.raster.amplitude = amp
            self.raster.phase = phase
            self.rasters.append(self.raster)
            return (True, "")
        else:
            return (False, "pna.getTrace returned no data")

            
