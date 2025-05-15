from abc import ABC, abstractmethod
from pydantic import BaseModel
from Controllers.PowerDetect.Interface import PowerDetect_Interface
from INSTR.SignalGenerator.Interface import SignalGenInterface
from Controllers.schemas.DeviceInfo import DeviceInfo
from DBBand6Cart.schemas.WCA import WCA
from Controllers.schemas.LO import LOSettings

class AutoRFStatus(BaseModel):
    is_active: bool = False
    last_output: float = None
    last_measured: float = None

class RFSource_Interface(ABC):

    @abstractmethod
    def getDeviceInfo(self) -> DeviceInfo:
        pass

    @abstractmethod
    def getConfig(self) -> int:
        pass

    @abstractmethod
    def setConfig(self, config: int) -> None:
        pass

    @abstractmethod
    def setFrequency(self, 
             freqGHz: float,
             settings: LOSettings = None
        ) -> tuple[bool, str]:
        pass

    @abstractmethod
    def setOutputPower(self, percent: float) -> tuple[bool, str]:
        pass

    @abstractmethod
    def getPAVD(self) -> float:
        pass

    @abstractmethod
    def getAutoRFStatus(self) -> AutoRFStatus:
        pass

    @abstractmethod
    def autoRFPower(self, 
            powerDetect: PowerDetect_Interface,
            targetSBPower: float,
            reinitialize: bool = False,
            **kwargs
        ) -> tuple[bool, str]:
        pass
