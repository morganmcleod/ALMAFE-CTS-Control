from abc import ABC, abstractmethod
from enum import Enum
from ALMAFE.basic.Units import Units
from Control.schemas.DeviceInfo import DeviceInfo

class DetectMode(Enum):
    METER = 'METER'
    SPEC_AN = 'SPEC_AN'
    PNA = 'PNA'
    VOLT_METER = 'VOLT_METER'

class PowerDetect_Interface(ABC):

    @abstractmethod
    def configure(self, **kwargs) -> None:
        pass
    
    @abstractmethod
    def reset(self) -> None:
        pass

    @property
    @abstractmethod    
    def device_info(self) -> DeviceInfo:
        pass

    @property
    @abstractmethod
    def detect_mode(self) -> DetectMode:
        pass

    @property
    @abstractmethod
    def units(self) -> Units:
        pass

    @abstractmethod
    def read(self, **kwargs) -> float | tuple[list[float], list[float]]:
        pass

    @abstractmethod
    def zero(self) -> None:
        pass
    