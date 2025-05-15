from abc import ABC, abstractmethod
from enum import Enum
from DBBand6Cart.schemas import PreampParam
from Measure.Shared.SelectLNA import SelectLNA

class LNABias_Interface(ABC):

    @abstractmethod
    def set_bias(self, 
            select: SelectLNA,
            config: PreampParam,
        ) -> tuple[bool, str]:
        pass

    @abstractmethod
    def set_enable(self, 
            select: SelectLNA, 
            enable: bool
        ) -> tuple[bool, str]:
        pass

    @abstractmethod
    def read_bias(self, select: SelectLNA) -> dict:
        pass
