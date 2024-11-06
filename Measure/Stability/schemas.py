from DBBand6Cart.TestResults import DataStatus
from pydantic import BaseModel
from datetime import datetime

class Settings(BaseModel):
    sampleRate: float = 20      # samples/sec
    sensorAmbient: int = 5
    attenuateIF: int = 3
    targetLevel: float = -10    # dBm
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
    timeSeriesPlot: int = None
    allanPlot: int = None
    tau0Seconds: float = 0.05

class StabilitySample(BaseModel):
    key: int = None
    timeStamp: datetime
    amp_or_phase: float
    temperature: float
