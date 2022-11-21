from enum import Enum
from pydantic import BaseModel
from typing import List, Optional
from CTSDevices.MotorControl.GalilDMCSocket import MotorController, MoveStatus, Position
from time import time, sleep
from datetime import datetime
import concurrent.futures

class ScanPort(Enum):
    POL0_USB = 1
    POL0_LSB = 2
    POL1_USB = 3
    POL1_LSB = 4

class SourcePosition(Enum):
    POL0_COPOL = 1
    POL1_COPOL = 2
    POL0_180 = 3

class SubScansOption(BaseModel):
    copol0: bool = True
    xpol0: bool = True
    copol1: bool = True
    xpol1: bool = True
    copol180: bool = True

    def getText(self):
        return f"{'C0 ' if self.copol0 else ''}" + \
               f"{'X0 ' if self.xpol0 else ''}" + \
               f"{'C1 ' if self.copol1 else ''}" + \
               f"{'X1 ' if self.xpol1 else ''}" + \
               f"{'180' if self.copol180 else ''}"

class SubScan(BaseModel):
    index: int = None
    pol: int
    isCopol: bool
    is180: bool = False

    def getText(self):
        return f"Pol{self.pol} {'copol' if self.isCopol else 'xpol'}{' 180' if self.is180 else ''}"

class ScanListItem(BaseModel):
    index: int = 0
    enable: bool = True
    RF: float
    LO: float
    subScansOption: SubScansOption = SubScansOption()
    subScansText: str = ""
    subScans: List[SubScan] = []
    
    def getText(self):
        return f"{'enabled' if self.enable else 'disabled'}: RF={self.RF} LO={self.LO}: {self.subScansOption.getText()}"
    
    def makeSubScans(self):
        self.subScans = []
        if self.subScansOption.copol0:
            self.subScans.append(SubScan(pol = 0, isCopol = True))
        if self.subScansOption.xpol0:
            self.subScans.append(SubScan(pol = 0, isCopol = False))
        if self.subScansOption.copol1:
            self.subScans.append(SubScan(pol = 1, isCopol = True))
        if self.subScansOption.xpol1:
            self.subScans.append(SubScan(pol = 1, isCopol = False))
        if self.subScansOption.copol180:
            self.subScans.append(SubScan(pol = 0, isCopol = True, is180 = True))
        index = 0
        for subScan in self.subScans:
            subScan.index = index
            index += 1

class ScanList(BaseModel):
    items: List[ScanListItem] = []

    def updateIndex(self):
        index = 0
        for item in self.items:
            item.index = index
            index += 1
            item.subScansText = item.subScansOption.getText()

class MeasurementSpec(BaseModel):
    beamCenter: Position = Position(x=146.5, y=144)
    scanStart: Position = Position(x=73, y=77)
    scanStop: Position = Position(x=223, y=217)
    resolution: float = 0.5
    scanAngles: List[float] = [13.5, 103.5]
    levelAngles: List[float] = [13.5, 103.5]
    targetLevel: float = -5.0
    centersInterval: float = 300 # 5 minutes

    def makeYAxisList(self) -> List[float]:
        y = float(self.scanStart.y)
        result = []
        while y <= self.scanStop.y:
            result.append(y)
            y += float(self.resolution)
        # append final value if needed:
        if result[-1] < self.scanStop.y:
            result.append(float(self.scanStop.y))
        return result

class ScanStatus(BaseModel):
    key: int = 0
    fkBeamPatterns: int = 0
    amplitude: float = -999
    phase: float = 0
    timeStamp: Optional[datetime] = None
    scanComplete: bool = False
    measurementComplete: bool = False
    activeScan: int = None
    activeSubScan: str = None
    message: str = None
    error: bool = False

class BeamScanner():

    def __init__(self, mc: MotorController):
        self.mc = mc
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers = 3)
        self.measurementSpec = MeasurementSpec()
        self.scanList = ScanList()
        self.__reset()
        
    def __reset(self):
        self.scanStatus = ScanStatus()

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

    def __runAllScans(self):
        self.scanList.updateIndex()
        for item in self.scanList.items:
            if item.enable:
                self.__reset()
                self.scanStatus.activeScan = item.index
                print(item.getText())
                item.makeSubScans()
                for subScan in item.subScans:
                    if self.stopNow:
                        self.__abortScan()
                        return
                    print(subScan.getText())
                    self.scanStatus.message = "Started: " + subScan.getText()
                    self.scanStatus.activeSubScan = subScan.getText()
                    self.__runOneScan(item, subScan)
                    self.scanStatus.activeSubScan = None
                self.scanStatus.activeScan = None
        self.scanStatus.measurementComplete = True

    def __runOneScan(self, scan, subScan) -> bool:
        # TODO: setup LO and RF, database, etc.
        lastCenterPwrTime = None
        # loop on y axis:
        for y in self.measurementSpec.makeYAxisList():
            # check for user stop signal
            if self.stopNow:
                self.__abortScan()
                return False
            # time to record the beam center power?
            if not lastCenterPwrTime or (time() - lastCenterPwrTime) > self.measurementSpec.centersInterval:
                lastCenterPwrTime = time()
                status = self.__measureCenterPower(pol = subScan.pol, scanComplete = False)
                if status.isError():
                    self.__abortScan(f"__measureCenterPower error {status.getText()}")
                    return False
            # check for user stop signal
            if self.stopNow:
                self.__abortScan()
                return False
            # go to start of this raster:
            nextPos = Position(x = self.measurementSpec.scanStart.x, y = y, pol = self.measurementSpec.scanAngles[subScan.pol])
            status = self.__moveScanner(nextPos, False)
            if status.isError():
                self.__abortScan(f"move to raster start error {status.getText()}")
                return False
            # move with triggering to the end of this raster:
            nextPos = Position(x = self.measurementSpec.scanStop.x, y = y, pol = self.measurementSpec.scanAngles[subScan.pol])
            status = self.__moveScanner(nextPos, True)
            if status.isError():
                self.__abortScan(f"move to raster end error {status.getText()}")
                return False

        # record the beam center power a final time:
        status = self.__measureCenterPower(pol = subScan.pol, scanComplete = True)
        if status.isError():
            self.__abortScan(f"final measureCenterPower error {status.getText()}")
            return False
        else:
            return True

    def __moveScanner(self, nextPos:Position, withTrigger:bool) -> MoveStatus:
        timeout = self.mc.estimateMoveTime(self.mc.getPosition(), nextPos)
        # print(f"move to {nextPos.getText()} trigger={withTrigger} timeout={timeout}")
        self.mc.setNextPos(nextPos)
        self.mc.startMove(withTrigger, timeout)
        # wait for move to complete:
        moveStatus = self.mc.getMoveStatus()
        while not self.stopNow and not moveStatus.shouldStop():
            sleep(timeout / 10)
            moveStatus = self.mc.getMoveStatus()
        return moveStatus

    def __measureCenterPower(self, pol: int, scanComplete = False) -> MoveStatus:
        self.measurementSpec.beamCenter.pol = self.measurementSpec.levelAngles[pol]
        moveStatus = self.__moveScanner(self.measurementSpec.beamCenter, False)
        # TODO error check and trigger measurement
        sleep(1)
        self.scanStatus.timeStamp = datetime.now()
        self.scanStatus.scanComplete = scanComplete
        return moveStatus

    def __abortScan(self, msg = "scan stopped"):
        print(msg)
        self.scanStatus.activeScan = None
        self.scanStatus.activeSubScan = None
        self.scanStatus.message = msg
        self.scanStatus.error = True
