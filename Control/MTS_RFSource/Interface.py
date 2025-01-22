from abc import ABC, abstractmethod
from PowerDetect.Interface import PowerDetect_Interface

class SidebandSource_Interface(ABC):

    @abstractmethod
    def setFrequency(self, freqGHz: float) -> tuple[bool, str]:
        pass

    @abstractmethod
    def setOutputPower(self, percent: float) -> tuple[bool, str]:
        pass

    @abstractmethod
    def getMonitorData(self) -> dict:
        pass

    @abstractmethod
    def autoRFPower(self, 
            powerDetect: PowerDetect_Interface,
            targetSBPower: float,
            reinitialize: bool = False
        ) -> tuple[bool, str]:
        pass


