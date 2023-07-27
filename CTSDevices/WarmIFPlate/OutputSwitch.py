from CTSDevices.SwitchController.HP3488a import SwitchController, SwitchConfig, DigitalPort, DigitalMethod
from enum import Enum
import time

class PadSelect(Enum):
    PAD_OUT = 0
    PAD_IN = 1          # this is also the bit of the control word to send

class LoadSelect(Enum):
    LOAD = 0
    THROUGH = 4         # this is also the bit of the control word to send

class OutputSelect(Enum):
    POWER_METER = 0
    SQUARE_LAW = 16      # this is also the bit of the control word to send
    
class OutputSwitch():
    def __init__(self, resource="GPIB0::9::INSTR", reset: bool = True):
        """Constructor

        :param str resource: VISA resource string, defaults to "GPIB0::9::INSTR"
        """
        self.switchController = SwitchController(resource, writeConfig = SwitchConfig(
            slot = 2,
            port = DigitalPort.LOW_ORDER_8BIT
        ))
        if reset:
            self.reset()

    def reset(self) -> None:
        self.setValue()

    def setValue(self, output: OutputSelect = OutputSelect.POWER_METER, 
                       load: LoadSelect = LoadSelect.THROUGH,
                       pad: PadSelect = PadSelect.PAD_OUT) -> None:
        # send the compliment of the byte having the selected bits:
        self.switchController.staticWrite(255)
        time.sleep(0.2)
        self.switchController.staticWrite(255 - (output.value + load.value + pad.value))

