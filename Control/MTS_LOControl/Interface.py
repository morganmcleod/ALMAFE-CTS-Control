from abc import ABC, abstractmethod
from ..MTS_SISBias.Interface import SISBias_interface

class LOControl_interface(ABC):

    @abstractmethod
    def setYTOLimits(self, ytoLowGHz: float, ytoHighGHz: float) -> None:
        pass

    @abstractmethod
    def setFrequency(self, freqGHz: float) -> tuple[bool, str]:
        pass

    @abstractmethod
    def setOutputPower(self, percent: float) -> tuple[bool, str]:
        pass

    @abstractmethod
    def getMonitorData(self) -> dict:
        pass
    
    def autoLOPower(self, 
            sisBias: SISBias_interface, 
            targetMixerCurrent: float,
            reinitialize: bool = False
        ) -> tuple[bool, str]:
        pass
