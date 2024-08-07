from abc import ABC, abstractmethod
from enum import Enum
from INSTR.InputSwitch.Interface import InputSelect
from Control.schemas.DeviceInfo import DeviceInfo

class OutputSelect(Enum):
    POWER_DETECT = 'POWER'
    PNA_INTERFACE = 'PNA'
    LOAD = 'LOAD'

class IFSystem_Interface(ABC):

    @abstractmethod
    def reset(self) -> None:
        pass

    @property
    @abstractmethod    
    def device_info(self) -> DeviceInfo:
        pass

    @property
    @abstractmethod
    def input_select(self) -> InputSelect:
        pass
    
    @input_select.setter
    @abstractmethod
    def input_select(self, inputSelect: InputSelect):
        pass
    
    @abstractmethod
    def set_pol_sideband(self, pol: int = 0, sideband: int | str = 'USB') -> None:
        pass

    @property
    @abstractmethod
    def output_select(self) -> OutputSelect:
        pass

    @output_select.setter
    @abstractmethod
    def output_select(self, outputSelect: OutputSelect):
        pass
    
    @property
    @abstractmethod
    def frequency(self) -> float:
        pass
    
    @frequency.setter
    @abstractmethod
    def frequency(self, freq_GHz: float):
        pass

    @property
    @abstractmethod
    def attenuation(self) -> float:
        pass

    @attenuation.setter
    @abstractmethod
    def attenuation(self, atten_dB: float):
        pass
    