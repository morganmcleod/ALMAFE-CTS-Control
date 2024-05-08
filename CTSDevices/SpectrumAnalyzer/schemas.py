from enum import Enum

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
