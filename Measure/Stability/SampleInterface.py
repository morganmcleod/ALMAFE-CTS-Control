from AmpPhaseDataLib.Constants import Units, DataKind
from abc import ABC, abstractmethod
from typing import Tuple, Optional

class SampleInterface(ABC):
    @abstractmethod
    def configure(self) -> None:
        pass

    @abstractmethod
    def getSample(self) -> Tuple[float, Optional[float]]:
        pass

    @abstractmethod
    def getUnits(self) -> Tuple[Units, Optional[Units]]:
        pass

    @abstractmethod
    def getDataKind(self) -> DataKind:
        pass