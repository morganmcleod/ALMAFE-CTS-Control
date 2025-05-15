from enum import Enum
from abc import ABC, abstractmethod
from Measure.Shared.SelectSIS import SelectSIS
from Measure.MixerTests import ResultsQueue
from Measure.MixerTests.ResultsInterface import ResultsInterface
from AMB.schemas.MixerTests import MagnetOptSettings, DefluxSettings
from Controllers.SIS.Interface import SISBias_Interface

class SISMagnet_Interface(ABC):

    @abstractmethod
    def setCurrent(self,
            currentMA: float,
            sisSelect: SelectSIS = SelectSIS.SIS1
        ) -> tuple[bool, str]:
        pass
    
    @abstractmethod
    def readCurrent(self,
            averaging: int = 1,
            sisSelect: SelectSIS = SelectSIS.SIS1
        ) -> float:
        pass

    @abstractmethod
    def magnetOptimize(self,
            settings: MagnetOptSettings,
            resultsTarget: ResultsInterface,
            sisBias: SISBias_Interface
        ) -> tuple[bool, str]:
        pass

    @abstractmethod
    def mixersDeflux(self,
            settings: DefluxSettings,
            resultsTarget: ResultsInterface
        ) -> tuple[bool, str]:
        pass

    @abstractmethod
    def stop(self):
        pass