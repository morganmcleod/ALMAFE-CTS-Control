from abc import ABC, abstractmethod
from typing import Tuple

class SignalGenInterface(ABC):

    @abstractmethod
    def idQuery(self, doPrint = False) -> bool:
        return True

    @abstractmethod
    def reset(self):
        pass

    @abstractmethod
    def errorQuery(self) -> Tuple[bool, str]:
        return 0, "No error"

    @abstractmethod
    def isConnected(self) -> bool:
        return True
    
    @abstractmethod
    def setAmplitude(self, amp_dB:float) -> bool:
        return True

    @abstractmethod
    def setFrequency(self, freq_GHz:float) -> bool:
        return True
        
    @abstractmethod
    def setRFOutput(self, enable:bool) -> bool:
        return True
        
    @abstractmethod
    def getAmplitude(self) -> float:
        return 0

    @abstractmethod
    def getFrequency(self) -> float:
        return 0

    @abstractmethod
    def getRFOutput(self) -> bool:
        return True
