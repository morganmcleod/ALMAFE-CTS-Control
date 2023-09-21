from DBBand6Cart.TestResults import DataStatus
from pydantic import BaseModel
from datetime import datetime

class Settings(BaseModel):
    sampleRate: float = 50      # samples/sec
    sensorAmbient: int = 7
    delayAfterLock: float = 10  # minutes
    measureDuration: float = 60 # minutes
    measurePol0: bool = True
    measurePol1: bool = True
    measureUSB: bool = True
    measureLSB: bool = True
    loStart: float = 221.0
    loStop: float = 265.0
    loStep: float = 22.0

class TimeSeriesInfo(BaseModel):
    key: int = None             # timeSeriesId assigned by database
    freqLO: float
    pol: int
    sideband: str
    timeStamp: datetime
    dataStatus: str
