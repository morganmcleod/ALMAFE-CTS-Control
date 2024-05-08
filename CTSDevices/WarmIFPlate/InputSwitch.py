from CTSDevices.SwitchController.HP3488a import SwitchController, SwitchConfig, DigitalPort, DigitalMethod
from enum import Enum
from typing import Union

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
        self.position = None
        self.setValue(InputSelect.POL0_USB)

    def isConnected(self) -> bool:
        return self.switchController.isConnected()

    def setValue(self, select: InputSelect) -> None:
        # send the compliment of the byte having the selected bit:
        self.switchController.staticWrite(255 - select.value)
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
        return True
