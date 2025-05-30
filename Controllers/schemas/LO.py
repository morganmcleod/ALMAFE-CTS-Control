from pydantic import BaseModel
from typing import Optional
from enum import Enum
from AMB.LODevice import LODevice

class LoopBW(Enum):
    '''
    Loop Bandwidth options
    
    -1 = DEFAULT: use the band's default loop bandwidth.
     0 = NORMAL: override to use the "normal" loop BW:   7.5MHz/V (Band 2,4,8,9)
     1 = ALT: override to use the "alternate" loop BW: 15MHz/V (Band 3,5,6,7,10, and NRAO band 2 prototype)
    '''
    DEFAULT = -1
    NORMAL  = 0
    ALT     = 1 

class LockSB(Enum):
    '''
    Lock Sideband options
    0 = BELOW_REF: lock below the reference signal
    1 = ABOVE_REF: lock above the reference signal
    '''     
    BELOW_REF = 0 
    ABOVE_REF = 1 

class ConfigYTO(BaseModel):
    '''
    YIG Tuned Oscillator configuration
    
    lowGHz and highGHz are the tuning range endpoints.    
    '''
    lowGHz: float
    highGHz: float
    def getText(self):
        return f"{self.lowGHz} - {self.highGHz} GHz"
    
class YTO(ConfigYTO):
    '''
    YIG Tuned Oscillator course tune setting, plus everything in ConfigYTO.
    
    courseTune in 0..4095 
    '''
    courseTune: int
    ytoFreqGHz: float
    def getText(self):
        return f"{self.courseTune} in ({super(YTO, self).getText()}) freq:{self.ytoFreqGHz}"

class LOSettings(BaseModel):
    lockLO: bool = True
    setReference: bool = False      # should the reference synth be set up before locking
    refAmplitude: float = -20       # dBm reference synth amplitude
    refAmplitudeMax: float | None = None   # increase amplitude up to this max if provided
    floogOffset: float = 0.01       # GHz
    loopBWSelect: int = LODevice.LOOPBW_ALT     # 15 MHz/V
    lockSBSelect: int = LODevice.LOCK_BELOW_REF

class AdjustPLL(BaseModel):
    '''
    While locked, adjust the course tuning to achieve the target correction voltage
    
    targetCV: requested correction voltage 
    '''
    targetCV:Optional[float] = 0
    def getText(self):
        return f"CV:{self.targetCV} V"

class LockInfo(BaseModel): 
    '''
    Phase Locked Loop monitor data: lock quality info only
    
    lockVoltage: True if the lock detector voltage > 3.0
    unlockDetected: Hardware latches True if an unlock condition was seen since last cleared
    refTP: Reference total power detector. Negative voltage in -5..0.
    IFTP: IF total power detector. Negative voltage in -5..0.
    isLocked: True if lockVoltage > 3.0
    '''   
    lockVoltage: float
    unlockDetected: bool
    refTP: float
    IFTP: float
    isLocked: bool
    def getText(self):
        return ("LOCKED " if self.isLocked else "UNLOCKED ") + \
               ("UNLOCK DETECTED " if self.unlockDetected else "OK ") + \
               f"refTP:{self.refTP} V  IFTP:{self.IFTP} V  lockDet:{self.lockVoltage}"
    
class PLL(LockInfo):
    '''
    All Phase Locked Loop monitor data, including everything in LockInfo
    
    courseTune: the YTO course tuning
    corrV: the PLL correction voltage in -10..10.
    temperature: the PLL assembly temperature in Celcius
    nullPLL: True if the PLL Null Integrator bit is set, defeating the PLL and forcing corrV to 0.
    '''
    loFreqGHz: float
    courseTune: int
    corrV: float
    temperature: float
    nullPLL: bool
    def getText(self):
        return super(PLL, self).getText() + \
               ("PLL NULLED" if self.nullPLL else "PLL normal") + \
               f" CV:{self.corrV} courseTune:{self.courseTune} temp:{self.temperature}"
    
class PLLConfig(BaseModel):
    '''
    Phase Locked Loop configuration
    
    loopBW: 0 or 1.  See description for class LoopBW(Enum) above.  If None, no change.
    lockSB: 0 or 1.  See description for class LockSB(Enum) above.  If None, no change.
    warmMult: Read only constant depends on band
    coldMult: Read only constant depends on band
    '''
    loopBW:Optional[int] = None 
    lockSB:Optional[int] = None
    warmMult:Optional[int] = None
    coldMult:Optional[int] = None
    def getText(self):
        ret = f"loopBW:{self.loopBW} " if (self.loopBW is not None) else ""
        if self.lockSB is not None:
            ret += f"lock:{'above ref' if self.lockSB else 'below ref'} "
        if self.warmMult is not None:
            ret += f"warmMult:{self.warmMult} "
        if self.coldMult is not None:
            ret += f"coldMult:{self.coldMult} "
        return ret
    
class Photomixer(BaseModel):
    '''
    Photimixer monitor data
    
    enabled: True if photomixer bias voltage is on.
    voltage: Photomixer bias voltage monitor
    current: Photomixer current monitor
    '''
    enabled: bool
    voltage: float
    current: float
    def getText(self):
        return ("ENABLED" if self.enabled else "DISABLED") + \
        f" current:{self.current} mA  voltage:{self.voltage} mV"
        
class AMC(BaseModel):
    '''
    Active Multiplier Chain monitor data
    
    For each stage:
    VD*: drain voltage
    ID*: drain current
    VG*: gate voltage
    multDCounts: multiplier D is configured with an integer digital pot setting
    multDCurrent: multiplied D current monitor
    supply5V: supply voltage monitor
    '''
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
    def getText(self):
        return f"VDA:{self.VDA} IDA:{self.IDA} VGA:{self.VGA} " + \
               f"VDB:{self.VDB} IDB:{self.IDB} VGB:{self.VGB} " + \
               f"VDE:{self.VDE} IDE:{self.IDE} VGE:{self.VGE} " + \
               f"multDCounts:{self.multDCounts} multDCurrent:{self.multDCurrent} supply5V:{self.supply5V}"

class SetPA(BaseModel):
    '''
    Power amplifier settings for one pol:
    pol: 0 or 1
    VDConrol: float in 0..2.5 unitless control value. If None, no change.
    VG: float in -0.8 to +0.15.  If None, no change.
    '''
    pol: int
    VDControl: Optional[float] = None
    VG: Optional[float] = None
    def getText(self):
        return f"pol:{self.pol} VDControl:{self.VDControl} VG:{self.VG}"
    
class PA(BaseModel):
    '''
    Power Amplifier monitor data
    
    VDp0, VDp1: drain voltage for pol0, pol1.
    IDp0, IDp1: drain current for pol0, pol1.
    VFp0, VGp1: gate voltage for pol0, pol1.
    supply3V, supply5V: supply voltage monitors
    '''
    VDp0: float
    VDp1: float
    IDp0: float
    IDp1: float
    VGp0: float
    VGp1: float
    supply3V: float 
    supply5V: float
    def getText(self):
        return f"VDp0:{self.VDp0} VDp1:{self.VDp1} IDp0:{self.IDp0} IDp1:{self.IDp1} VGp0:{self.VGp0} VGp1:{self.VGp1}" + \
               f"supply3V{self.supply5V} supply3V{self.supply5V}"
    
class TeledynePA(BaseModel):
    '''
    Teledyne Power Amplifier configuration.  Band 7 only as of 2022.
    
    hasTeledyne: if True, interpret VD settings as base voltage.
    collectorP0, P1: if hasTeledunePA, use these digital pot settings for collector voltage.
    '''
    hasTeledyne: bool
    collectorP0: Optional[int] = 0
    collectorP1: Optional[int] = 0
    def getText(self):
        return f"Teledyne PA configured: collector P0{self.collectorP0} P1{self.collectorP1}" if self.hasTeledyne else "No Teledyne PA"
