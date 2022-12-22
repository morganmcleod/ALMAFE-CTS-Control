'''
Data models and interface for three-axis motor controller
'''
from .schemas import *
from abc import ABC, abstractmethod
from typing import Tuple, List, Optional

class PNAInterface(ABC):

    @abstractmethod
    def idQuery(self) -> Optional[str]:
        """Perform an ID query and check compatibility
        :return str: manufacturer and model or None
        """
        pass

    @abstractmethod
    def errorQuery(self) -> Tuple[int, str]:
        pass
    
    @abstractmethod
    def reset(self) -> bool:
        """Reset instrument to defaults
        :return bool: True if reset successful
        """
        pass

    @abstractmethod
    def setMeasConfig(self, config: MeasConfig):
        """Set the measurement configuration for a channel
        :param MeasConfig config
        """
        pass

    @abstractmethod
    def setPowerConfig(self, config: PowerConfig):
        """Set the output power and attenuation configuration for a channel
        :param PowerConfig config
        """
        pass

    @abstractmethod
    def getTrace(self, *args, **kwargs) -> List[float]:
        """Get trace data as a list of float
        :return List[float]
        """
        pass

    
    @abstractmethod
    def getAmpPhase(self) -> Tuple[float]:
        """Get instantaneous amplitude and phase
        :return (amplitude_dB, phase_deg)
        """
        pass
