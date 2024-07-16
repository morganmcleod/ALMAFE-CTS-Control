from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

class DetectMode(Enum):
    METER = 'METER'
    SPEC_AN = 'SPEC_AN'
    PNA = 'PNA'

class PowerDetect_Interface(ABC):

    @abstractmethod
    def configure(self, **kwargs) -> None:
        pass

    @property
    @abstractmethod
    def detect_mode(self) -> DetectMode:
        pass

    @abstractmethod
    def read(self, **kwargs) -> float | tuple[list[float], list[float]]:
        pass

    @abstractmethod
    def zero(self) -> None:
        pass