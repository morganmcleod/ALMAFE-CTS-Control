from pydantic import BaseModel
from datetime import datetime
from DBBand6Cart.TestResults import DataStatus
from Measure.Shared.SelectPolarization import SelectPolarization
from Measure.Shared.SelectSideband import SelectSideband

class Settings(BaseModel):
    sampleRate: float = 20      # samples/sec
    sensorAmbient: int = 5
    attenuateIF: int = 3
    targetLevel: float = -10    # dBm
    delayAfterLock: float = 10  # minutes
    measureDuration: float = 60 # minutes
    polarization: str = SelectPolarization.BOTH.value
    sideband: str = SelectSideband.BOTH.value
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
    loCorrVPlot: int = None
    rfCorrVPlot: int = None
    spectrumPlot: int = None
    tau0Seconds: float = 0.05

class StabilitySample(BaseModel):
    key: int = None
    timeStamp: datetime
    amp_or_phase: float
    temperature: float
