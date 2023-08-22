from CTSDevices.MotorControl.schemas import Position
from pydantic import BaseModel
from enum import Enum
from typing import List, Optional
from datetime import datetime

class ScanPort(Enum):
    POL0_USB = 1
    POL0_LSB = 2
    POL1_USB = 3
    POL1_LSB = 4

class SourcePosition(Enum):
    POL0_COPOL = 1
    POL1_COPOL = 2
    POL0_180 = 3
    POL1_180 = 4

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

    def getScanAngleIndex(self) -> int:
        '''Compute which pol angle to use during scan
        
        Not isCopol means we are measuring port 'pol' but at the other polarization angle.
        '''
        if self.isCopol or self.is180:
            return self.pol
        return 1 - self.pol
    
    def getScanPort(self, isUSB:bool) -> ScanPort:
        '''Compute which port to sellect during scan.

        Always measure using port 'pol'.
        '''
        if self.pol == 0:
            return ScanPort.POL0_USB if isUSB else ScanPort.POL0_LSB
        else:
            return ScanPort.POL1_USB if isUSB else ScanPort.POL1_LSB

    def getSourcePosition(self) -> SourcePosition:
        if self.pol == 0:
            if self.isCopol:
                return SourcePosition.POL0_COPOL if not self.is180 else SourcePosition.POL0_180
            else:
                return SourcePosition.POL1_COPOL
        else:
            if self.isCopol:
                return SourcePosition.POL1_COPOL if not self.is180 else SourcePosition.POL1_180
            else:
                return SourcePosition.POL0_COPOL

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
    
    def isUSB(self):
        return self.RF > self.LO

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
    scanEnd: Position = Position(x=223, y=217)
    resolution: float = 0.5
    scanAngles: List[float] = [-103.5, -13.5]
    targetLevel: float = -5.0
    centersInterval: float = 300 # 5 minutes
    scanBidirectional: bool = True

    def makeYAxisList(self) -> List[float]:
        y = float(self.scanStart.y)
        result = []
        while y <= self.scanEnd.y:
            result.append(y)
            y += float(self.resolution)
        # append final value if needed:
        if result[-1] < self.scanEnd.y:
            result.append(float(self.scanEnd.y))
        return result
    
    def makeXAxisList(self) -> List[float]:
        x = float(self.scanStart.x)
        result = []
        while x <= self.scanEnd.x:
            result.append(x)
            x += float(self.resolution)
        # append final value if needed:
        if result[-1] < self.scanEnd.x:
            result.append(float(self.scanEnd.x))
        return result

    def numScanPoints(self) -> int:
        # Example cases:
        # start end   reso.  numpts
        # 1     3     1      3 
        # 1     2.9   1      2
        # 1     3.1   1      3
        return int(abs(self.scanEnd.x - self.scanStart.x) / self.resolution) + 1

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

    def getCenterPowerText(self):
        return f"{self.timeStamp}: {self.amplitude:.2f} dB, {self.phase:.2f} deg{' scanComplete' if self.scanComplete else ''}"

    def getText(self):
        return f"{self.key}:{self.fkBeamPatterns} active:{self.activeScan}:{self.activeSubScan} " \
                + self.getCenterPowerText() + f"{' measComplete' if self.measurementComplete else ''}" \
                + f" {'ERROR ' if self.error else ''}\'{self.message}\'"

class Raster(BaseModel):
    key: int = 0                    # keyBeamPattern
    index: int = 0
    startPos:Position = Position()
    xStep: float = 0
    amplitude:List[float] = []
    phase:List[float] = []

    def __eq__(self, other):
        return self.index == other.index and self.key == other.key

class Rasters(BaseModel):
    items: List[Raster] = []

    def getStartIndex(self) -> int:
        if len(self.items):
            return self.items[0].index
        else:
            return 0
    
    def getLastIndex(self) -> int:
        if len(self.items):
            return self.items[-1].index
        else:
            return 0

