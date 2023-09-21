from .InputSwitch import InputSelect
from .OutputSwitch import PadSelect, LoadSelect, OutputSelect
from typing import Union

class AttenuatorSimulator():
    def __init__(self):
        self.reset()

    def reset(self):
        self.value = 100

    def setValue(self, atten: int = 20):
        self.value = atten
        
    def getValue(self):
        return self.value

class InputSwitchSimulator():
    def __init__(self):
        self.position = InputSelect.POL0_USB

    def setValue(self, select: InputSelect) -> None:
        self.position = select

    def getValue(self) -> InputSelect:
        return self.position
    
    def setPolAndSideband(self, pol: int, sideband: Union[int, str]) -> bool:
        if pol not in (0, 1):
            return False
        if isinstance(sideband, str):
            if sideband.upper() == 'USB':
                sideband = 0
            elif sideband.upper() == 'LSB':
                sideband = 1
            else:
                return False
        if pol == 0:
            if sideband == 0:
                self.setValue(InputSelect.POL0_USB)
            elif sideband == 1:
                self.setValue(InputSelect.POL0_LSB)
        else:
            if sideband == 0:
                self.setValue(InputSelect.POL1_USB)
            elif sideband == 1:
                self.setValue(InputSelect.POL1_LSB)
        return False

class NoiseSourceSimulator():
    def __init__(self):
        self.reset()

    def reset(self) -> None:
        pass

    def setEnable(self, enable: bool = False) -> None:
        pass

class OutputSwitchSimulator():
    def __init__(self):
        self.reset()

    def reset(self) -> None:
        pass

    def setValue(self, output: OutputSelect = OutputSelect.POWER_METER, 
                       load: LoadSelect = LoadSelect.THROUGH,
                       pad: PadSelect = PadSelect.PAD_OUT) -> None:
        pass

class YIGFilterSimulator():
    def __init__(self, resource="GPIB0::9::INSTR"):
        self.reset()

    def reset(self):
        self.freqGhz = 1

    def setFrequency(self, freqGHz: float) -> None:
        self.freqGhz = freqGHz

    def getFrequency(self) -> float:
        return self.freqGhz        





