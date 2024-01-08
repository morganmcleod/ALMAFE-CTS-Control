from pydantic import BaseModel
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
from datetime import datetime

class StabilityRecord(BaseModel):
    key: int = None                 # assigned by the database on insert
    fkCartTest: int
    fkRawData: int                  # References the raw data in SQLite on the measurement system
    timeStamp: datetime
    freqLO: float
    freqCarrier: float
    pol: int
    sideband: int                   # 0=LSB, 1=USB
    time: float
    allan: float
    errorBar: float

class CalcDataInterface(ABC):
    @abstractmethod 
    def create(self, recors: List[StabilityRecord]) -> Tuple[bool, str]:
        pass

