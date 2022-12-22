from pydantic import BaseModel
from enum import Enum

class MeasType(Enum):
    S11 = "S11"
    S12 = "S12"
    S21 = "S21"
    S22 = "S22"
    A = "A"
    B = "B"
    R1 = "R1"
    R2 = "R2"
    AB = "AB"
    BA = "BA"

class Format(Enum):
    FDATA = "FDATA" # formatted trace data from measResult location
    SDATA = "SDATA" # corrected complex trace data from rawMeas location
    FMEM = "FMEM"   # formatted memory data from memResult location
    SMEM = "SMEM"   # corrected complex data from rawMemory location
    SDIV = "SDIV"   # complex data from Normalization Divisor location

class SweepType(Enum):
    LIN_FREQ = "LIN"
    LOG_FREQ = "LOG"
    POWER_SWEEP = "POW"
    CW_TIME = "CW"
    SEGMENT_SWEEP = "SEGM"

class SweepGenType(Enum):
    ANALOG = "ANAL" # The sweep is controlled by an internally generated sweep ramp. 
                    # The phase lock loop maintains the proper association with the measurement. 
                    # This mode is faster than STEPPED. Sweep time can be set in this mode.

    STEPPED = "STEP" # The analyzer phase locks the source and receiver at each frequency point
                    # before making a measurement. This mode is more accurate than ANALOG.
                    # Dwell time can be set in this mode.

class TriggerSource(Enum):
    IMMEDIATE = "IMM"   # Internal source sends continuous trigger signals
    EXTERNAL = "EXT"    # External (rear panel) source 
    MANUAL = "MAN"      # Sends one trigger signal when manually triggered from the front panel
                        # or software trigger is sent.

class MeasConfig(BaseModel):
    channel: int = 1         # in 1..32
    measType: MeasType = MeasType.S21
    format: Format = Format.SDATA
    sweepType: SweepType = SweepType.CW_TIME
    sweepGenType: SweepGenType = SweepGenType.STEPPED
    sweepPoints: int = 20    # in 2..16001
    triggerSource: TriggerSource = TriggerSource.MANUAL
    bandWidthHz: int = 20e3  # in 1..250000.  Not all values are supported.
                             # Analyzer will round up to the next valid setting.
    centerFreq_Hz: int = 6e9 # Valid range is instrument-dependent
    spanFreq_Hz: int = 1e9   # Valid range is instrument-dependent.  Typical is 10e6..20e9
    timeout_sec: float = 10  # Sets selected channel sweep time value, if sweepGenType is ANALOG,
                             # or sets the selected channel dwell time value, if sweepGenType is STEPPED. 
                             # Note: Only set if "Sweep Time Auto" is "Off".
    sweepTimeAuto: bool = True
    measName: str = "MY_MEAS"
    def getText(self):
        return f"{self.measName}:CH{self.channel}:{self.measType.value}:{self.sweepType.value}:" + \
               f"center {self.centerFreq_Hz}, span {self.spanFreq_Hz}, BW {self.bandWidthHz}, {self.sweepPoints} points"


class PowerConfig(BaseModel):
    channel: int = 1                # in 1..32
    powerLevel_dBm: float = -10.0   # Channel output power in -90..+20
    attenuation_dB: float = 0.0     # Channel attenuation in 0..70
                                    # Note: Step is 10 dB. If a number other than these is entered, 
                                    # the analyzer will select the next lower valid value. For example, 
                                    # if 19.9 is entered, the analyzer will switch in 10 dB attenuation.
    def getText(self):
        return f"CH{self.channel}:power {self.powerLevel_dBm}, atten {self.attenuation_dB}"

class Mode(Enum):
    CREATE = 0
    DELETE = 1
    SELECT = 2

class TriggerScope(Enum):
    ALL_CHANNELS = "ALL"
    CURRENT_CHANNEL = "CURR"

class TriggerLevel(Enum):
    LOW = "LOW"
    HIGH = "HIGH"

class TriggerMode(Enum):
    HOLD = "HOLD"
    CONTINUOUS = "CONT"
    COUNT = "GRO"

class DataFormat(Enum):
    REAL32 = "REAL,32"
    REAL64 = "REAL,64"
    ASCII = "ASCII"

class DataOrder(Enum):
    NORMAL = "NORM"
    SWAP = "SWAP"