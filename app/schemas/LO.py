from pydantic import BaseModel
from enum import Enum

class LoopBW(Enum):
    DEFAULT = -1    # use the band's default loop bandwidth
    NORMAL  = 0     # override to use the "normal" loop BW:   7.5MHz/V (Band 2,4,8,9)
    ALT     = 1     # override to use the "alternate" loop BW: 15MHz/V (Band 3,5,6,7,10, and NRAO band 2 prototype)

class LockSB(Enum): 
    BELOW_REF = 0   # lock below the reference signal
    ABOVE_REF = 1   # lock above the reference signal

class YTO(BaseModel):
    courseTune: int
    lowGhz: float
    highGhz: float

class LockInfo(BaseModel):    
    lockDetectBit: bool
    unlockDetected: bool
    refTP: float
    IFTP: float
    isLocked: bool
    
class PLL(LockInfo):
    courseTune: int
    corrV: float
    temperature: float
    nullPLL: bool
    
class PLLConfig(BaseModel):
    loopBW:LoopBW
    lockSB:LockSB
    
class Photomixer(BaseModel):
    enabled: bool
    voltage: float
    current: float
    
class AMC(BaseModel):
    VGA: float
    VDA: float
    IDA: float
    VGB: float
    VDB: float
    IDB: float
    VGE: float
    VDE: float
    IDE: float
    multDCounts: int
    multDCurrent: float
    supply5V: float
    
class PA(BaseModel):
    VGp0: float
    VGp1: float
    VDp0: float
    VDp1: float
    IDp0: float
    IDp1: float
    supply3V: float 
    supply5V: float
    
class TeledynePA(BaseModel):
    hasTeledyne: bool
    collectorP0: int
    collectorP1: int
    