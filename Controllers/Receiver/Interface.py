from abc import ABC, abstractmethod
from DBBand6Cart.schemas.MixerParam import MixerParam
from Controllers.schemas.DeviceInfo import DeviceInfo
from Controllers.schemas.LO import LOSettings
from Controllers.IFSystem.Interface import IFSystem_Interface
from Controllers.LO.Interface import AutoLOStatus
from Measure.MixerTests.ResultsInterface import ResultsInterface
from Measure.Shared.SelectPolarization import SelectPolarization
from Measure.Shared.SelectSIS import SelectSIS
from AMB.schemas.MixerTests import *
from AMB.CCADevice import IFPowerInterface
from INSTR.Chopper.Interface import Chopper_Interface

class Receiver_Interface(ABC):

    @abstractmethod
    def reset(self) -> None:
        pass

    @abstractmethod
    def getDeviceInfo() -> DeviceInfo:
        pass
    
    @abstractmethod
    def setConfig(self, configId: int) -> tuple[bool, str]:
        pass

    @abstractmethod
    def getConfig(self) -> int:
        pass

    @abstractmethod
    def is2SB(self) -> bool:
        pass

    @abstractmethod
    def getPLL(self) -> dict:
        pass

    @abstractmethod
    def getPA(self) -> dict:
        pass

    @abstractmethod
    def setBias(self, FreqLO:float, magnetOnly: bool = False) -> tuple[bool, str]:
        pass

    @abstractmethod
    def setSISbias(self,
            select: SelectSIS,
            bias_mV: float,
            imag_mA: float
        ) -> tuple[bool, str]:
        pass

    @abstractmethod
    def readSISBias(self, select: SelectSIS, **kwargs) -> dict:
        pass

    @abstractmethod
    def getLastSISRead(self, select: SelectSIS) -> dict:
        pass

    @abstractmethod
    def setPAOutput(self, pol: SelectPolarization, percent: float) -> None:
        pass

    @abstractmethod
    def getPAOutput(self, pol: SelectPolarization) -> float:
        pass

    @abstractmethod
    def autoLOPower(self, reinitialize: bool = False, **kwargs) -> tuple[bool, str]:
        pass

    @abstractmethod
    def getAutoLOStatus(self) -> AutoLOStatus:
        pass

    @abstractmethod
    def getTargetMixersBias(self, freqLO: float = None) -> tuple[MixerParam] | None:
        pass

    @abstractmethod
    def setFrequency(self, 
            freqGHz:float, 
            settings: LOSettings
        ) -> tuple[bool, str]:
        pass

    @abstractmethod
    def isLocked(self) -> bool:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def ivCurve(self, 
            settings: IVCurveSettings, 
            resultsTarget: ResultsInterface,
            ifPowerDetect: IFPowerInterface | None = None,
            ifSystem: IFSystem_Interface | None = None,
            chopper: Chopper_Interface | None = None
        ) -> None:
        pass

    @abstractmethod
    def magnetOptimize(self, 
            settings: MagnetOptSettings, 
            resultsTarget: ResultsInterface
        ) -> tuple[bool, str]:
        pass

    @abstractmethod
    def mixersDeflux(self,
            settings: DefluxSettings,
            resultsTarget: ResultsInterface
        ) -> tuple[bool, str]:
        pass