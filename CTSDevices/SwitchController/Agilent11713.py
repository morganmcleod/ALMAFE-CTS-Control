from typing import Sequence

from CTSDevices.Common.VisaInstrument import VisaInstrument

class AttenuatorSwitchController():
    """The Agilent 11713A Atten/switch controller"""
    
    DEFAULT_TIMEOUT = 15000     # milliseconds
    
    def __init__(self, resource="GPIB0::28::INSTR", reset=True):
        """Constructor

        :param str resource: VISA resource string
        :param bool idQuery: If true, perform an ID query and check compatibility, defaults to True
        :param bool reset: If true, reset the instrument and set default configuration, defaults to True
        """
        self.connected = False
        self.inst = VisaInstrument(resource, timeout = self.DEFAULT_TIMEOUT)
        if reset:
            self.reset()

    def reset(self):
        self.setSwitches(tuple(False * 10))

    def isConnected(self) -> bool:
        return self.inst.connected and self.connected

    def setSwitch(self, index: int, value: bool = False) -> None:
        if index < 1 or index > 10:
            raise ValueError("AttenuatorSwitchController.setSwitch: index out of range (1..10)")
        if index == 10:
            index = 0
        cmd = "A" if value else "B"
        try:
            self.inst.write(f"{cmd}{index}")
        except:
            self.logger.error("Not connected to 11713B/C switch controller")
            self.connected = False

    def setSwitches(self, switches: Sequence[bool]) -> None:
        if len(switches) != 10:
            raise ValueError("AttenuatorSwitchController.setSwitches: switches must be a sequence of 10 bool")
        
        cmd = ""
        for i in range(len(switches)):
            cmd += "A" if switches[i] else "B"
            cmd += str((i + 1) % 10)   # convert 0..9 to 1..0
        try:
            self.inst.write(cmd)
        except:
            self.logger.error("Not connected to 11713B/C switch controller")
            self.connected = False

        