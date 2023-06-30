from TestEquipment.HP3488a import SwitchController, SwitchConfig, DigitalPort, DigitalMethod
from enum import Enum

class InputSelect(Enum):
    POL0_USB = 1
    POL0_LSB = 2
    POL1_USB = 3
    POL1_LSB = 4
    NOISE_DIODE = 5
    INPUT6 = 6

class InputSwitch():
    def __init__(self, resource="GPIB0::9::INSTR"):
        """Constructor

        :param str resource: VISA resource string, defaults to "GPIB0::9::INSTR"
        """
        self.switchController = SwitchController(resource)
        self.switchController.writeConfig = SwitchConfig(
            slot = 1,
            port = DigitalPort.LOW_ORDER_8BIT,
            method = DigitalMethod.BINARY,
        )

    def setValue(self, select: InputSelect) -> None:
        if select == InputSelect.NOISE_DIODE:
            dataOut = 64
        elif select == InputSelect.INPUT6:
            dataOut = 128
        else:
            dataOut = 2 ^ (select.value - 1)
        self.switchController.staticWrite(255 - dataOut)

