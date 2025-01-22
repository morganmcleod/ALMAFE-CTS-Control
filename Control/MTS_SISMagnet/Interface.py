from abc import ABC, abstractmethod
from ..MTS_SISBias.Interface import SelectBias

class SISMagnet_interface(ABC):

    @abstractmethod
    def setCurrent(self,
            currentMA: float,
            sisSelect: SelectBias = SelectBias.SIS1
        ) -> tuple[bool, str]:
        pass
    
    @abstractmethod
    def readCurrent(self,
            averaging: int = 1,
            sisSelect: SelectBias = SelectBias.SIS1
        ) -> float:
        pass
