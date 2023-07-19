from CTSDevices.SwitchController.HP3488a import SwitchController, SwitchConfig, DigitalPort, DigitalMethod
from enum import Enum

class InputSelect(Enum):
    POL0_USB = 1            # these are also the bits of the control word to send
    POL0_LSB = 2
    POL1_USB = 4
    POL1_LSB = 8
    NOISE_DIODE = 64
    INPUT6 = 32

class InputSwitch():
    def __init__(self, resource="GPIB0::9::INSTR"):
        """Constructor

        :param str resource: VISA resource string, defaults to "GPIB0::9::INSTR"
        """
        self.switchController = SwitchController(resource, writeConfig = SwitchConfig(
            slot = 1,
            port = DigitalPort.LOW_ORDER_8BIT
        ))

    def setValue(self, select: InputSelect) -> None:
        # send the compliment of the byte having the selected bit:
        self.switchController.staticWrite(255 - select.value)
