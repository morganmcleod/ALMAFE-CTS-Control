from CTSDevices.SwitchController.Agilent11713 import AttenuatorSwitchController
from enum import Enum
from typing import Union

class ExtInputSelect(Enum):
    USB = 1
    LSB = 2
    NOISE_DIODE = 3

class ExternalSwitch():

    POS1 = (True, False, False, False, False, False, False, False, False, False)
    POS2 = (False, True, False, False, False, False, False, False, False, False)
    POS3 = (False, False, True, False, False, False, False, False, False, False)
    ALL_OFF = (False, False, False, False, True, False, False, False, False, False)

    def __init__(self, resource="GPIB0::29::INSTR", simulate: bool = False):
        """Constructor

        :param str resource: VISA resource string,
        """
        self.simulate = simulate
        self.switchController = AttenuatorSwitchController(resource)
        self.switchController.setSwitches(self.ALL_OFF)
        self.position = None
        self.setValue(ExtInputSelect.USB)

    def isConnected(self) -> bool:
        return self.switchController.isConnected()

    def setValue(self, select: ExtInputSelect) -> None:
        self.position = select
        if self.simulate:
            return
        if select == ExtInputSelect.USB:
            self.switchController.setSwitches(self.POS1)
        elif select == ExtInputSelect.LSB:
            self.switchController.setSwitches(self.POS2)
        elif select == ExtInputSelect.NOISE_DIODE:
            self.switchController.setSwitches(self.POS3)
        else:
            self.position = None
            self.switchController.setSwitches(self.switchController.RESET)

    def getValue(self) -> ExtInputSelect | None:
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
                self.setValue(ExtInputSelect.USB)
            elif sideband == 1:
                self.setValue(ExtInputSelect.LSB)
        else:
            if sideband == 0:
                self.setValue(ExtInputSelect.USB)
            elif sideband == 1:
                self.setValue(ExtInputSelect.LSB)
        return True
