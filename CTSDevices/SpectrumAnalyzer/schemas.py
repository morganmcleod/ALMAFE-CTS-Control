from enum import Enum
from pydantic import BaseModel

class InternalPreamp(Enum):
    OFF = "OFF"
    LOW_BAND = "BAND LOW"
    FULL_RANGE = "BAND FULL"

class LevelUnits(Enum):
    DBM = "DBM"
    DBMV = "DBMV"
    DBMA = "DBMA"
    W = "W"
    V = "V"
    DBUV = "DBUV"
    DBUA = "DBUA"

class DetectorMode(Enum):
    NORMAL = "NORM"
    AVERAGE = "AVER"
    PEAK = "POS"
    SAMPLE = "SAMP"
    NEGATIVE_PEAK = "NEG"

class TraceType(Enum):
    CLEAR_WRITE = "WRIT"
    AVERAGE = "AVER"
    MAX_HOLD = "MAXH"
    MIN_HOLD = "MINH"

class AveragingType(Enum):
    AUTO = "AUTO ON"
    RMS = "RMS"
    LOG = "LOG"
    SCALAR = "SCAL"

class MarkerType(Enum):
    NORMAL = "POS"
    DELTA = "DELT"
    FIXED = "FIX"
    OFF = "OFF"

class MarkerReadout(Enum):
    AUTO = "AUTO ON"
    FREQUENCY = "FREQ"
    PERIOD = "PER"
    TIME = "TIME"
    INVERSE_TIME = "ITIM"

class SpectrumAnalyzerSettings(BaseModel):
    sweepPoints: int = 2001
    attenuation: float = 2
    enableInternalPreamp: bool = False
    autoResolutionBW: bool = False
    resolutionBW: float = 8e6
    autoVideoBW: bool = False
    videoBW: float = 1e3
    autoSweepTime: bool = True
    sweepTime: float = 0.0663
    enableAveraging: bool = False
    averagingCount: int = 1