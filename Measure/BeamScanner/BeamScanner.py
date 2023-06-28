from CTSDevices.MotorControl.schemas import MoveStatus, Position
from CTSDevices.MotorControl.MCInterface import MCInterface
from CTSDevices.PNA.schemas import MeasConfig, PowerConfig, MeasType, SweepType, Format, SweepGenType, TriggerSource
from CTSDevices.PNA.PNAInterface import PNAInterface
from CTSDevices.PNA.AgilentPNA import DEFAULT_CONFIG, FAST_CONFIG, DEFAULT_POWER_CONFIG
from CTSDevices.SignalGenerator.Keysight_PSG_MXG import SignalGenerator
from AMB.LODevice import LODevice
from AMB.CCADevice import CCADevice
from simple_pid import PID
from .schemas import MeasurementSpec, ScanList, ScanListItem, ScanStatus, SubScan, Raster, Rasters
from time import time, sleep
from datetime import datetime
import concurrent.futures
from typing import Tuple
import copy

class BeamScanner():

    XY_SPEED_POSITIONING = 40 # mm/sec
    XY_SPEED_SCANNING = 20    # mm/sec
    POL_SPEED = 20            # deg/sec

    def __init__(self, 
                motorController:MCInterface, 
                pna:PNAInterface, 
                loReference:SignalGenerator, 
                ccaDevice:CCADevice, 
                loDevice:LODevice, 
                rfSrcDevice:LODevice):
        self.mc = motorController
        self.pna = pna
        self.loReference = loReference
        self.rfReference = None     # normally we don't use the RF source reference synth.  Set this to do so for debugging.
        self.ccaDevice = ccaDevice
        self.loDevice = loDevice
        self.rfSrcDevice = rfSrcDevice
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
        print("BeamScanner: stopped")

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
                print(scan.getText())
                scan.makeSubScans()
                for subScan in scan.subScans:
                    if self.stopNow:
                        self.__abortScan("User Stop")
                        return
                    print(subScan.getText())
                    self.scanStatus.message = "Started: " + subScan.getText()
                    self.scanStatus.activeSubScan = subScan.getText()
                    success, msg = self.__runOneScan(scan, subScan)
                    print(f"{success}:{msg}")
                    self.scanStatus.activeSubScan = None
                self.scanStatus.activeScan = None
        self.scanStatus.measurementComplete = True
        self.scanStatus.message = "Scan complete"

    def __runOneScan(self, scan:ScanListItem, subScan:SubScan) -> Tuple[bool, str]:
        success, msg = self.__resetRasters()
        if success:
            success, msg = self.__setWarmIFInput(scan, subScan)
        if success:
            success, msg = self.__rfSourceOff()
        if success:
            success, msg = self.__lockLO(scan, subScan)
        if success:
            success, msg = self.__setReceiverBias(scan, subScan)
        if success:
            success, msg = self.__lockRF(scan, subScan)
        if success:
            success, msg = self.__setYIGFilter(scan, subScan)
        if success:
            success, msg = self.__moveToBeamCenter(scan, subScan)
        if success:
            success, msg = self.__rfSourceAutoLevel(scan, subScan)
       
        if not success:
            return (success, msg)

        lastCenterPwrTime = None
        rasterIndex = 0;
        # loop on y axis:
        for yPos in self.measurementSpec.makeYAxisList():

            # check for User Stop signal
            if self.stopNow:
                self.__abortScan("User Stop")
                return False

            # time to record the beam center power?
            if not lastCenterPwrTime or (time() - lastCenterPwrTime) > self.measurementSpec.centersInterval:
                lastCenterPwrTime = time()
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

    def __moveScanner(self, nextPos:Position, withTrigger:bool, moveTimeout = None) -> Tuple[bool, str]:
        self.mc.setXYSpeed(self.XY_SPEED_SCANNING if withTrigger else self.XY_SPEED_POSITIONING)
        self.mc.setPolSpeed(self.POL_SPEED)
        if not moveTimeout:
            moveTimeout = self.mc.estimateMoveTime(self.mc.getPosition(), nextPos)
        # print(f"move to {nextPos.getText()} trigger={withTrigger} moveTimeout={moveTimeout}").
        self.mc.setNextPos(nextPos)
        self.mc.startMove(withTrigger, moveTimeout)
        moveStatus = self.mc.getMoveStatus()
        while not self.stopNow and not moveStatus.shouldStop():
            sleep(0.1)                
            moveStatus = self.mc.getMoveStatus()
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
        self.scanStatus.amplitude, self.scanStatus.phase = self.pna.getAmpPhase()
        self.scanStatus.timeStamp = datetime.now()
        self.scanStatus.scanComplete = scanComplete
        print(self.scanStatus.getCenterPowerText())
        return (True, "__measureCenterPower")

    def __abortScan(self, msg) -> Tuple[bool, str]:
        print(msg)
        self.scanStatus.activeScan = None
        self.scanStatus.activeSubScan = None
        self.scanStatus.message = msg
        self.scanStatus.error = True
        return (False, msg)

    def __resetPNA(self) -> Tuple[bool, str]:
        self.pna.reset()
        self.pnaConfig = copy(DEFAULT_CONFIG)        
        self.pnaConfig.triggerSource = TriggerSource.EXTERNAL
        self.pna.setMeasConfig(self.pnaConfig)
        self.pna.setPowerConfig(DEFAULT_POWER_CONFIG)
        code, msg = self.pna.errorQuery()
        return (code == 0, "__resetPNA: " + msg)

    def __resetRasters(self) -> Tuple[bool, str]:
        self.rasters = []
        self.nextRaster = -1
        return (True, "")

    def __setWarmIFInput(self, scan:ScanListItem, subScan:SubScan) -> Tuple[bool, str]:
        return (True, "")

    def __rfSourceOff(self) -> Tuple[bool, str]:
        self.rfSrcDevice.setPAOutput(pol =0, percent = 0)
        return (True, "")

    def __lockLO(self, scan:ScanListItem, subScan:SubScan) -> Tuple[bool, str]:
        self.loDevice.selectLockSideband(self.loDevice.LOCK_ABOVE_REF)
        wcaFreq, ytoFreq, ytoCourse = self.loDevice.setLOFrequency(scan.LO)
        if wcaFreq > 0:
            pllConfig = self.loDevice.getPLLConfig()
            self.loReference.setFrequency((scan.LO / pllConfig['coldMult'] - 0.020) / pllConfig['warmMult'])
            self.loReference.setAmplitude(12.0)
            self.loReference.setRFOutput(True)
            wcaFreq, ytoFreq, ytoCourse = self.loDevice.lockPLL()
        msg = f"__lockLO: wca={wcaFreq}, yto={ytoFreq}, courseTune={ytoCourse}"
        return (wcaFreq != 0, msg)

    def __setReceiverBias(self, scan:ScanListItem, subScan:SubScan) -> Tuple[bool, str]:
        return (True, "")

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

    def __setYIGFilter(self, scan:ScanListItem, subScan:SubScan) -> Tuple[bool, str]:
        return (True, "")

    def __moveToBeamCenter(self, scan:ScanListItem, subScan:SubScan) -> Tuple[bool, str]:
        self.measurementSpec.beamCenter.pol = self.measurementSpec.levelAngles[subScan.pol]
        success, msg = self.__moveScanner(self.measurementSpec.beamCenter, withTrigger = False)
        return (success, "__moveToBeamCenter: " + msg)

    def __rfSourceAutoLevel(self, scan:ScanListItem, subScan:SubScan) -> Tuple[bool, str]:
        self.pna.setMeasConfig(FAST_CONFIG)
        controller = PID(0.02, 0.012, 0.012, setpoint=self.measurementSpec.targetLevel)
        controller.output_limits = (15, 100)
        setValue = 15 # percent
        iter = 100
        amp, phase = self.pna.getAmpPhase()
        if not amp:
            msg = f"__rfSourceAutoLevel: getAmpPhase error."
            return (False, msg)
        self.rfSrcDevice.setPAOutput(subScan.pol, setValue) 
        while iter > 0 and not (self.measurementSpec.targetLevel - 1) < amp < (self.measurementSpec.targetLevel + 1):
            setValue = controller(amp)
            self.rfSrcDevice.setPAOutput(subScan.pol, setValue)
            amp, phase = self.pna.getAmpPhase()
            if not amp:
                msg = f"__rfSourceAutoLevel: getAmpPhase error at iter={iter}."
                return (False, msg)
            iter -= 1
        msg = f"__rfSourceAutoLevel: target={self.measurementSpec.targetLevel} amp={amp} setValue={setValue} iter={iter}"
        print(msg)
        return (iter > 0, msg)

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

            
