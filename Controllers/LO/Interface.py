from abc import ABC, abstractmethod
from pydantic import BaseModel
from Controllers.SIS.Interface import SISBias_Interface
from Controllers.schemas.DeviceInfo import DeviceInfo
from Controllers.schemas.LO import LOSettings

class AutoLOStatus(BaseModel):
    is_active: bool = False
    last_output: float = None
    last_measured: float = None

class LOControl_Interface(ABC):

    @abstractmethod
    def getDeviceInfo(self) -> DeviceInfo:
        pass

    # def setFrequency(self,
    #         freqGHz: float, 
    #         settings: LOSettings
    #     ) -> tuple[bool, str]:
    #     pass

    @abstractmethod
    def getPLL(self) -> dict:
        pass

    @abstractmethod
    def getPA(self) -> dict:
        pass

    @abstractmethod
    def setOutputPower(self, percent: float) -> None:
        pass
   
    @abstractmethod
    def getOuputPower(self) -> float:
        pass

    @abstractmethod
    def getAutoLOStatus(self) -> AutoLOStatus:
        pass

    @abstractmethod
    def autoLOPower(self, 
            sisBias: SISBias_Interface, 
            targetMixerCurrent: float,
            reinitialize: bool = False
        ) -> tuple[bool, str]:
        pass
