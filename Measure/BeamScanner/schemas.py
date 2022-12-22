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
    scanEnd: Position = Position(x=223, y=217)
    resolution: float = 0.5
    scanAngles: List[float] = [13.5, 103.5]
    levelAngles: List[float] = [13.5, 103.5]
    targetLevel: float = -5.0
    centersInterval: float = 300 # 5 minutes

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
        return f"{self.timeStamp}: {self.amplitude:.2} dB, {self.phase:.2} deg{' scanComplete' if self.scanComplete else ''}"

    def getText(self):
        return f"{self.key}:{self.fkBeamPatterns} active:{self.activeScan}:{self.activeSubScan} " \
                + self.getCenterPowerText() + f"{' measComplete' if self.measurementComplete else ''}" \
                + f" {'ERROR ' if self.error else ''}\'{self.message}\'"

class Raster(BaseModel):
    startPos:Position = Position()
    xStep:float = 0
    amplitude:List[float] = []
    phase:List[float] = []

class Rasters(BaseModel):
    startIndex:int = 0
    rasters:List[Raster] = []
