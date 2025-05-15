from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class StabilityPlot(BaseModel):
    key: int            # timeSeries ID
    fkCartTest: int
    fkTestType: int
    timeStamp: datetime
    freqLO: float
    pol: int
    sideband: str
    x: List[float]
    y: List[float]
    yError: Optional[List[float]] = None
