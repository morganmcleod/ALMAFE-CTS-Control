from INSTR.MotorControl.schemas import Position
from INSTR.MotorControl.MCInterface import MCInterface
from INSTR.PNA.schemas import TriggerSource
from INSTR.PNA.PNAInterface import PNAInterface
from INSTR.PNA.AgilentPNA import DEFAULT_CONFIG, FAST_CONFIG, DEFAULT_POWER_CONFIG
from INSTR.SignalGenerator.Keysight_PSG_MXG import SignalGenerator
from Control.IFSystem.Interface import IFSystem_Interface, InputSelect, OutputSelect
from AMB.LODevice import LODevice
from Control.CartAssembly import CartAssembly
from Control.RFAutoLevel import RFAutoLevel
from Control.IFSystem.Interface import IFSystem_Interface
from Control.PowerDetect.PDPNA import PDPNA
from .schemas import MeasurementSpec, ScanList, ScanListItem, ScanStatus, SubScan, Raster, Rasters
from ..Shared.MeasurementStatus import MeasurementStatus
from DBBand6Cart.CartTests import CartTest
from app.database.CTSDB import CartTestsDB
from DBBand6Cart.BPCenterPowers import BPCenterPower, BPCenterPowers
from DBBand6Cart.BeamPatterns import BeamPattern, BeamPatterns
from DBBand6Cart.BPRawData import BPRawDatum, BPRawData
from DBBand6Cart.BPErrors import BPErrorLevel, BPError, BPErrors
from app.database.CTSDB import CTSDB
from DebugOptions import *

import os
import time
from datetime import datetime
import concurrent.futures
from typing import Tuple
import copy
import logging
import yaml

class BeamScanner():

    MEASUREMENT_SETTINGS_FILE = "Settings/Settings_BeamScanner.yaml"
    XY_SPEED_POSITIONING = 40       # mm/sec
    XY_SPEED_SCANNING = 20          # mm/sec
    POL_SPEED = 10                  # deg/sec
    
    def __init__(self, 
            motorController: MCInterface,
            pna: PNAInterface, 
            loReference: SignalGenerator, 
            cartAssembly: CartAssembly,
            rfSrcDevice: LODevice,
            ifSystem: IFSystem_Interface,            
            measurementStatus: MeasurementStatus):
        
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.mc = motorController
        self.pna = pna
        self.loReference = loReference
        self.rfReference = None     # normally we don't use the RF source reference synth.  Set this to do so for debugging.
        self.cartAssembly = cartAssembly
        self.rfSrcDevice = rfSrcDevice
        self.ifSystem = ifSystem
        self.measurementStatus = measurementStatus
        self.pdPNA = PDPNA(pna)
        self.rfAutoLevel = RFAutoLevel(self.ifSystem, self.pdPNA, self.rfSrcDevice)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers = 2)
        self.measurementSpec = None
        self.scanList = ScanList()
        self.futures = None
        self.keyCartTest = 0
        self.centerPowersTable = BPCenterPowers(driver = CTSDB())
        self.beamPatternsTable = BeamPatterns(driver = CTSDB())
        self.bpRawDataTable = BPRawData(driver = CTSDB())
        self.bpErrorsTable = BPErrors(driver = CTSDB())
        self.loadSettings()
        self.__reset()
        
    def __reset(self):
        self.scanStatus = ScanStatus(key = self.keyCartTest)
        self.__resetRasters()
        self.scanAngle = 0
        self.levelAngle = 0
        self.reverseX = False
        self.rasterReady = False
        self.yPos = 0
        self.stopNow = False

    def loadSettings(self):
        try:
            with open(self.MEASUREMENT_SETTINGS_FILE, "r") as f:
                d = yaml.safe_load(f)
                self.measurementSpec = MeasurementSpec.parse_obj(d)
        except:
            self.defaultSetttings()

    def defaultSetttings(self):
        self.measurementSpec = MeasurementSpec()
        self.saveSettings()

    def saveSettings(self):
        with open(self.MEASUREMENT_SETTINGS_FILE, "w") as f:
            yaml.dump(self.measurementSpec.dict(), f)

    def getLatestRasterInfo(self) -> tuple[int, int]:
        if len(self.rasters):
            return self.rasters[-1].key, self.rasters[-1].index
        else:
            return 0, 0

    def getRasters(self, 
                   first: int = 0, 
                   last: int = -1,
                   latestOnly: bool = False) -> Rasters:
        """Return a subset of the rasters collected so far

        :param int first: Start of range to retrieve.
        :param int last: End of range to retrieve.  -1 means get all the rest.
        :param bool latestOnly: If True, ignore first and last.  Instead return the most recent raster.
        :return Rasters
        """
        available = len(self.rasters)
        if latestOnly:
            # return the last raster if available
            if available:
                return Rasters(items = [self.rasters[-1]])
            else:
                # nothing to return:
                return Rasters()
        
        if last < first or last >= available:
            last = available - 1

        # return what's requested, if available:
        if 0 <= first < available:
            return Rasters(items = self.rasters[first:last])
        else:
            return Rasters()
        
    def start(self, cartTest: CartTest) -> int:
        cartTestsDb = CartTestsDB()
        if not SIMULATE:
            self.keyCartTest = cartTestsDb.create(cartTest)
        else:
            self.keyCartTest = 1
        
        self.measurementStatus.setComplete(False)
        self.measurementStatus.setStatusMessage("Started")
        
        self.stopNow = False
        self.scanStatus = ScanStatus()
        # make this not None for now, so client will display that measurement has started:
        self.scanStatus.activeScan = 0
        self.futures = []
        self.futures.append(self.executor.submit(self.__runAllScans))
        # self.futures.append(self.executor.submit(self.__databaseWriterThread))
        return self.keyCartTest

    def stop(self):
        self.stopNow = True
        self.mc.stopMove()
        if self.futures:
            concurrent.futures.wait(self.futures)
        self.logger.info("BeamScanner: stopped")

    def isMeasuring(self):
        return not self.scanStatus.scanComplete

    def __runAllScans(self) -> None:
        success, msg = self.__resetRasters();        
        if not success:
            return
        success, msg = self.__resetPNA()
        if not success:
            self.__logBPError(
                source = self.__runAllScans.__name__,
                msg = msg
            )
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
                    self.scanStatus.activeSubScanIndex = subScan.index
                    self.scanStatus.activeSubScan = subScan.getText()

                    # compute angles for this scan:
                    self.scanAngle = self.measurementSpec.scanAngles[subScan.getScanAngleIndex()]
                    self.levelAngle = self.measurementSpec.scanAngles[subScan.pol]
                    if subScan.is180:
                        self.scanAngle += 180
                        self.levelAngle += 180

                    # create the BeamPatterns record for this scan:
                    if SIMULATE:
                        keyId = 1
                    else:
                        keyId = self.beamPatternsTable.create(BeamPattern(
                            fkCartTest = self.keyCartTest,
                            FreqLO = scan.LO,
                            FreqCarrier = scan.RF,
                            Beam_Center_X = self.measurementSpec.beamCenter.x,
                            Beam_Center_Y = self.measurementSpec.beamCenter.y,                        
                            Scan_Angle = self.scanAngle,
                            Scan_Port = subScan.getScanPort(scan.isUSB()).value,
                            Lvl_Angle = self.levelAngle,
                            AutoLevel = self.measurementSpec.targetLevel,
                            Resolution = self.measurementSpec.resolution,
                            SourcePosition = subScan.getSourcePosition().value
                        ))
                    if not keyId:
                        msg = "__runAllScans: beamPatternsTable.create returned None"
                        success = False
                    else:
                        # run the scan:
                        self.scanStatus.fkBeamPatterns = keyId
                        self.xAxisList = self.measurementSpec.makeXAxisList()
                        self.yAxisList = self.measurementSpec.makeYAxisList()
                        success, msg = self.__runOneScan(scan, subScan)

                    self.scanStatus.activeSubScanIndex = None
                    self.scanStatus.activeSubScan = None
                    
                    if success:
                        self.logger.info(f"{success}:{msg}")
                        self.scanStatus.message = "Scan complete"
                    else:
                        self.scanStatus.message = "Error: " + msg
                        self.__logBPError(
                            source = self.__runAllScans.__name__, 
                            msg = msg,
                            freqSrc = scan.RF,
                            freqRcvr = scan.LO
                        )

                self.scanStatus.activeScan = None
        self.scanStatus.scanComplete = True
        self.scanStatus.measurementComplete = True
        self.measurementStatus.setMeasuring(None)

    def __runOneScan(self, scan:ScanListItem, subScan:SubScan) -> Tuple[bool, str]:
        try:
            success, msg = self.__resetRasters()
            if success:
                success, msg = self.__configureIfProcessor(scan, subScan)
            if success:
                success, msg = self.__rfSourceOff()
            if success:
                success, msg = self.__lockLO(scan, subScan)
            if not success:
                # retry lock
                time.sleep(1)
                success, msg = self.__lockLO(scan, subScan)
            if success:
                success, msg = self.__setReceiverBias(scan, subScan)
            if success:
                success, msg = self.__lockRF(scan, subScan)
            if not success:
                time.sleep(1)
                # retry lock
                success, msg = self.__lockRF(scan, subScan)
            if success:
                success, msg = self.__moveToBeamCenter(scan, subScan)
            if success:
                success, msg = self.__rfSourceAutoLevel(scan, subScan)
            if success:
                success, msg = self.__measureCenterPower(scan, subScan, scanComplete = False)
                lastCenterPwrTime = time.time()
            
            if not success:
                self.__logBPError(
                    source = self.__runOneScan.__name__, 
                    msg = msg,
                    freqSrc = scan.RF,
                    freqRcvr = scan.LO
                )
                return (success, msg)

            self.__selectIFInput(isUSB = scan.RF > scan.LO, pol = subScan.pol)

            rasterIndex = 0
            # loop on y axis:
            for self.yPos in self.yAxisList:
                # are we scanning right-to-left at this yPos?
                self.reverseX = self.measurementSpec.scanBidirectional and (rasterIndex % 2 != 0)

                # check for User Stop signal
                if self.stopNow:
                    self.__abortScan("User Stop")
                    return (False, "User Stop")
                
                # check for motor power failure:
                motorStatus = self.mc.getMotorStatus()
                msg = "__runOneScan: motor power failure. Aborting all scans!"
                if motorStatus.powerFail():
                    self.__logBPError(
                        source = self.__runOneScan.__name__, 
                        msg = msg,
                        freqSrc = scan.RF,
                        freqRcvr = scan.LO
                    )
                    self.stopNow = True
                    self.__abortScan("Motor power failure")
                    return (False, "Motor power failure")
                
                # check for lost LO lock:
                lockInfo = self.cartAssembly.loDevice.getLockInfo()
                if not lockInfo['isLocked'] and not SIMULATE:
                    msg = "__runOneScan: lost LO lock. Aborting this scan."
                    self.__logBPError(
                        source = self.__runOneScan.__name__, 
                        msg = msg,
                        freqSrc = scan.RF,
                        freqRcvr = scan.LO
                    )
                    self.__abortScan("LOST LO LOCK")
                    return (False, "LOST LO LOCK")

                # check for lost RF source lock:
                lockInfo = self.rfSrcDevice.getLockInfo()
                if not lockInfo['isLocked'] and not SIMULATE:
                    msg = "__runOneScan: lost RF source lock. Aborting this scan."
                    self.__logBPError(
                        source = self.__runOneScan.__name__, 
                        msg = msg,
                        freqSrc = scan.RF,
                        freqRcvr = scan.LO
                    )
                    self.__abortScan("LOST RF SOURCE LOCK")
                    return (False, "LOST RF SOURCE LOCK")

                # time to record the beam center power?
                # always coming from +X direction to avoid mechanical backlash
                if self.reverseX and (not lastCenterPwrTime or (time.time() - lastCenterPwrTime) > self.measurementSpec.centersInterval):
                    lastCenterPwrTime = time.time()

                    success, msg = self.__measureCenterPower(scan, subScan, scanComplete = False)
                    if not success:
                        self.__logBPError(
                            source = self.__runOneScan.__name__, 
                            msg = msg,
                            freqSrc = scan.RF,
                            freqRcvr = scan.LO
                        )
                        self.__abortScan(msg)
                        return (success, msg)

                # check for User Stop signal
                if self.stopNow:
                    self.__abortScan("User Stop")
                    return (False, "User Stop")

                # go to start of this raster:
                startPos = Position(
                    x = self.measurementSpec.scanStart.x, 
                    y = self.yPos, 
                    pol = self.scanAngle
                )
                endPos = Position(
                    x = self.measurementSpec.scanEnd.x, 
                    y = self.yPos, 
                    pol = self.scanAngle
                )
                xStep = self.measurementSpec.resolution

                if self.reverseX:
                    startPos, endPos = endPos, startPos
                    xStep = -xStep
                
                self.raster = Raster(
                    key = self.scanStatus.fkBeamPatterns,
                    index = rasterIndex,
                    startPos = startPos,
                    xStep = xStep
                )

                success, msg = self.__moveScanner(startPos, withTrigger = False)
                if not success:
                    self.__logBPError(
                        source = self.__runOneScan.__name__, 
                        msg = msg,
                        freqSrc = scan.RF,
                        freqRcvr = scan.LO
                    )
                    self.__abortScan(msg)
                    return (success, msg)

                # configure external triggering:
                self.mc.setXYSpeed(self.XY_SPEED_SCANNING)
                moveTimeout = self.mc.estimateMoveTime(self.mc.getPosition(), endPos)
                success, msg = self.__configurePNARaster(scan, subScan, moveTimeout)
                if not success:
                    self.__logBPError(
                        source = self.__runOneScan.__name__, 
                        msg = msg,
                        freqSrc = scan.RF,
                        freqRcvr = scan.LO
                    )
                    self.__abortScan(msg)
                    return (success, msg)

                # start the move:
                success, msg = self.__moveScanner(endPos, withTrigger = True)
                if not success:
                    self.__logBPError(
                        source = self.__runOneScan.__name__, 
                        msg = msg,
                        freqSrc = scan.RF,
                        freqRcvr = scan.LO
                    )
                    self.__abortScan(msg)
                    return (success, msg)
                
                # get the PNA trace data:
                success, msg = self.__getPNARaster(scan, subScan)
                if not success:
                    self.__logBPError(
                        source = self.__runOneScan.__name__, 
                        msg = msg,
                        freqSrc = scan.RF,
                        freqRcvr = scan.LO
                    )
                    self.__abortScan(msg)
                    return (success, msg)

                # Write to database:
                success, msg = self.__writeRasterToDatabase(scan, subScan)      # removed worker thread
                rasterIndex += 1                                          # removed worker thread
                
            # record the beam center power a final time:
            success, msg = self.__measureCenterPower(scan, subScan, scanComplete = True)
            if not success:
                self.__logBPError(
                    source = self.__runOneScan.__name__, 
                    msg = msg,
                    freqSrc = scan.RF,
                    freqRcvr = scan.LO
                )
                self.__abortScan(msg)
                return (success, msg)
            else:
                return (True, "__runOneScan complete")
        except Exception as e:
            self.logger.exception(e)
            return (False, "__runOneScan Exception: " + str(e))

    def __moveScanner(self, nextPos:Position, withTrigger:bool) -> Tuple[bool, str]:
        self.mc.setXYSpeed(self.XY_SPEED_SCANNING if withTrigger else self.XY_SPEED_POSITIONING)
        self.mc.setPolSpeed(self.POL_SPEED)
        moveTimeout = self.mc.estimateMoveTime(self.mc.getPosition(), nextPos)
        self.mc.setNextPos(nextPos)
        self.mc.startMove(withTrigger, moveTimeout)
        moveStatus = self.mc.waitForMove(timeout = moveTimeout + 0.5)
        actualPos = self.mc.getPosition(cached = False)
        self.mc.stopMove()
        if self.stopNow:
            return (False, "__moveScanner: User Stop")
        else:
            return (not moveStatus.isError(), f"__moveScanner: {moveStatus.getText()} nextPos: {nextPos.getText()} actual: {actualPos.getText()}")

    def __measureCenterPower(self, scan:ScanListItem, subScan:SubScan, scanComplete:bool = False) -> Tuple[bool, str]:
        success, msg = self.__moveToBeamCenter(scan, subScan)
        if not success:
            return (success, msg)
        self.pna.setMeasConfig(FAST_CONFIG)
        self.__selectIFInput(isUSB = scan.RF > scan.LO, pol = subScan.pol)

        self.pna.initContinuous()
        amp, phase = self.pna.getAmpPhase()        
        self.scanStatus.amplitude = amp if amp else -999
        self.scanStatus.phase = phase if phase else 0
        self.scanStatus.timeStamp = datetime.now()
        self.scanStatus.scanComplete = scanComplete
        if not SIMULATE:
            self.centerPowersTable.create(BPCenterPower(
                fkBeamPatterns = self.scanStatus.fkBeamPatterns, 
                Amplitude = self.scanStatus.amplitude,
                Phase = self.scanStatus.phase,
                ScanComplete = self.scanStatus.scanComplete
            ))
        self.logger.info(f"__measureCenterPower: position {self.mc.getPosition().getText()}")
        msg = f"__measureCenterPower: {self.scanStatus.getCenterPowerText()}"        
        self.logger.info(msg)
        return (True, msg)

    def __logBPError(self, source: str, msg: str, freqSrc = 0, freqRcvr = 0, level = BPErrorLevel.ERROR) -> None:
        self.logger.error(msg)
        if not SIMULATE:
            self.bpErrorsTable.create(BPError(
                fkBeamPattern = self.scanStatus.fkBeamPatterns,
                Level = level,
                Message = msg,
                Model = os.path.split(__file__)[1],
                Source = source,
                FreqSrc = freqSrc,
                FreqRcvr = freqRcvr
            ))

    def __abortScan(self, msg) -> Tuple[bool, str]:
        self.logger.info(msg)
        self.scanStatus.activeScan = None
        self.scanStatus.activeSubScanIndex = None
        self.scanStatus.activeSubScan = None
        self.scanStatus.message = msg
        self.scanStatus.error = True
        return (False, msg)

    def __resetPNA(self) -> Tuple[bool, str]:
        self.pna.reset()
        try:
            self.pna.workaroundPhaseLockLost()
        except:
            pass
        self.pnaConfig = copy.copy(DEFAULT_CONFIG)        
        self.pnaConfig.triggerSource = TriggerSource.EXTERNAL
        self.pna.setMeasConfig(self.pnaConfig)
        self.pna.setPowerConfig(DEFAULT_POWER_CONFIG)
        code, msg = self.pna.errorQuery()
        return (code == 0, "__resetPNA: " + msg)

    def __resetRasters(self) -> Tuple[bool, str]:
        self.rasters = []
        return (True, "")

    def __configureIfProcessor(self, scan:ScanListItem, subScan:SubScan) -> Tuple[bool, str]:
        self.__selectIFInput(isUSB = scan.RF > scan.LO, pol = subScan.pol)
        self.ifSystem.output_select = OutputSelect.PNA_INTERFACE
        self.ifSystem.frequency = abs(scan.RF - scan.LO)
        self.ifSystem.attenuation = self.measurementSpec.ifAttenuator
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
        self.ifSystem.input_select = position

    def __rfSourceOff(self) -> Tuple[bool, str]:
        self.rfSrcDevice.setPAOutput(pol = self.rfSrcDevice.paPol, percent = 0)
        return (True, "")

    def __lockLO(self, scan:ScanListItem, subScan:SubScan) -> Tuple[bool, str]:
        self.cartAssembly.loDevice.selectLockSideband(self.cartAssembly.loDevice.LOCK_ABOVE_REF)
        wcaFreq, ytoFreq, ytoCourse = self.cartAssembly.loDevice.setLOFrequency(scan.LO)
        pllConfig = self.cartAssembly.loDevice.getPLLConfig()
        self.loReference.setFrequency((scan.LO / pllConfig['coldMult'] - 0.020) / pllConfig['warmMult'])
        # self.loReference.setAmplitude(12.0)
        self.loReference.setRFOutput(True)
        if not SIMULATE:
            wcaFreq, ytoFreq, ytoCourse = self.cartAssembly.loDevice.lockPLL()
        return (True, f"__lockLO: wca={wcaFreq}, yto={ytoFreq}, courseTune={ytoCourse}")

    def __setReceiverBias(self, scan:ScanListItem, subScan:SubScan) -> Tuple[bool, str]:
        if self.cartAssembly.setRecevierBias(scan.LO):
            if not SIMULATE:
                ret = self.cartAssembly.autoLOPower()
            else:
                ret = False
            if ret or SIMULATE:
                return (True, "")
            else:
                return (False, "cartAssembly.autoLOPower failed")
        else:
            return (False, "cartAssembly.setRecevierBias failed.  Provide config ID?")

    def __lockRF(self, scan:ScanListItem, subScan:SubScan) -> Tuple[bool, str]:
        self.rfSrcDevice.selectLockSideband(self.rfSrcDevice.LOCK_ABOVE_REF)
        wcaFreq, ytoFreq, ytoCourse = self.rfSrcDevice.setLOFrequency(scan.RF)
        if self.rfReference:
            # for debug only.  Normally the RF ref synth is not used for beam patterns:
            pllConfig = self.rfSrcDevice.getPLLConfig()
            self.rfReference.setFrequency((scan.RF / pllConfig['coldMult'] - 0.020) / pllConfig['warmMult'])
            self.rfReference.setAmplitude(16.0)
            self.rfReference.setRFOutput(True)
        if not SIMULATE:
            wcaFreq, ytoFreq, ytoCourse = self.rfSrcDevice.lockPLL()
        return (wcaFreq != 0, f"__lockRF: wca={wcaFreq}, yto={ytoFreq}, courseTune={ytoCourse}")

    def __moveToBeamCenter(self, scan:ScanListItem, subScan:SubScan) -> Tuple[bool, str]:
        self.measurementSpec.beamCenter.pol = self.levelAngle
        success, msg = self.__moveScanner(self.measurementSpec.beamCenter, withTrigger = False)
        return (success, "__moveToBeamCenter: " + msg)

    def __rfSourceAutoLevel(self, scan:ScanListItem, subScan:SubScan) -> Tuple[bool, str]:
        self.pdPNA.configure(power_config = DEFAULT_POWER_CONFIG, config = FAST_CONFIG)
        success = self.rfAutoLevel.autoLevel(abs(scan.RF - scan.LO), self.measurementSpec.targetLevel)
        if SIMULATE:
            success = True
        return (success, "__rfSourceAutoLevel")

    def __configurePNARaster(self, scan:ScanListItem, subScan:SubScan, moveTimeout:float) -> Tuple[bool, str]:
        # add 10sec to timeout to account for accel/decel
        self.pnaConfig.timeout_sec = moveTimeout + 10
        self.pnaConfig.sweepPoints = self.measurementSpec.numScanPoints()
        self.pna.setMeasConfig(self.pnaConfig)
        return (True, "")

    def __getPNARaster(self, scan:ScanListItem, subScan:SubScan) -> Tuple[bool, str]:
        amp, phase = self.pna.getTrace(y = self.yPos, reverseX = self.reverseX)
        if amp and phase:
            self.raster.amplitude = amp
            self.raster.phase = phase
            self.raster.complete = True
            self.rasters.append(self.raster)
            return (True, "")
        else:
            return (False, "pna.getTrace returned no data")

    # def __databaseWriterThread(self):
    #     while not self.stopNow and not self.scanStatus.measurementComplete:
    #         if self.raster.complete:
    #             scan = self.scanList.items[self.scanStatus.activeScan]
    #             subScan = scan.subScans[self.scanStatus.activeSubScanIndex]
    #             self.__writeRasterToDatabase(scan, subScan)
    #             self.raster.complete = False
    #             self.raster.index += 1
    #         time.sleep(2)

    def __writeRasterToDatabase(self, scan: ScanListItem, subScan: SubScan) -> Tuple[bool, str]:
        if SIMULATE:
            return (True, "Simulate write to database")
        xAxisList = reversed(self.xAxisList) if self.reverseX else self.xAxisList
        now = datetime.now()
        records = [BPRawDatum(
            fkBeamPattern = self.scanStatus.fkBeamPatterns,
            Pol = subScan.pol,
            Position_X = x,
            Position_Y = self.yPos,
            SourceAngle = self.scanAngle,
            Power = amp,
            Phase = phase,
            timeStamp = now
        ) for x, amp, phase in zip(xAxisList, self.raster.amplitude, self.raster.phase)]

        count = self.bpRawDataTable.create(records)
        
        if count == len(self.xAxisList):
            return (True, "")
        else:
            msg = f"__writeRasterToDatabase: Only {count} records out of {len(self.xAxisList)} were written."
            self.__logBPError(
                source = self.__writeRasterToDatabase.__name__, 
                msg = msg,
                freqSrc = scan.RF,
                freqRcvr = scan.LO
            )
            return (False, msg)
        
