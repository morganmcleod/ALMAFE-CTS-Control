from abc import ABC, abstractmethod
from DBBand6Cart.schemas import PreampParam

class LNABias_interface(ABC):

    @abstractmethod
    def set_bias(self, 
            configLNA1: PreampParam,
            configLNA2: PreampParam
        ) -> tuple[bool, str]:
        pass

    @abstractmethod
    def set_enable(self, enable: bool) -> tuple[bool, str]:
        pass

    @abstractmethod
    def read_bias(self) -> dict:
        pass
