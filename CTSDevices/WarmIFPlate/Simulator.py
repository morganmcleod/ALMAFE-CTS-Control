from .InputSwitch import InputSelect
from .OutputSwitch import PadSelect, LoadSelect, OutputSelect

class AttenuatorSimulator():
    def __init__(self):
        self.reset()

    def reset(self):
        pass

    def setValue(self, atten: int = 20):
        pass

class InputSwitchSimulator():
    def __init__(self):
        pass

    def setValue(self, select: InputSelect) -> None:
        pass

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





