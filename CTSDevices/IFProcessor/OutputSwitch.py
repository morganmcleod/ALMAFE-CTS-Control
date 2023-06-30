from TestEquipment.HP3488a import SwitchController, SwitchConfig, DigitalPort, DigitalMethod
from enum import Enum

class OutputSelect(Enum):
    POWER_METER = 1
    SQUARE_LAW = 2

class LoadSelect(Enum):
    THROUGH = 1
    LOAD = 2

class OutputSwitch():
    def __init__(self, resource="GPIB0::9::INSTR", reset: bool = True):
        """Constructor

        :param str resource: VISA resource string, defaults to "GPIB0::9::INSTR"
        """
        self.switchController = SwitchController(resource)
        self.switchController.writeConfig = SwitchConfig(
            slot = 2,
            port = DigitalPort.LOW_ORDER_8BIT,
            method = DigitalMethod.BINARY,
        )
        if reset:
            self.reset()

    def reset(self) -> None:
        self.setValue(OutputSelect.POWER_METER, LoadSelect.THROUGH)

    def setValue(self, select: OutputSelect, loadSelect: LoadSelect) -> None:
        dataOut = 0
        if loadSelect == LoadSelect.THROUGH:
            dataOut += 32
        if select == OutputSelect.SQUARE_LAW:
            dataOut += 8
        self.switchController.staticWrite(255 - dataOut)

