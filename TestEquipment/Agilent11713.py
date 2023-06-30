from typing import Sequence
import pyvisa
import re

class AttenuatorSwitchController():
    """The Agilent 11713A Atten/switch controller"""
    
    DEFAULT_TIMEOUT = 15000     # milliseconds
    
    def __init__(self, resource="GPIB0::28::INSTR", reset=True):
        """Constructor

        :param str resource: VISA resource string
        :param bool idQuery: If true, perform an ID query and check compatibility, defaults to True
        :param bool reset: If true, reset the instrument and set default configuration, defaults to True
        """
        rm = pyvisa.ResourceManager()
        self.inst = rm.open_resource(resource)
        self.inst.timeout = self.DEFAULT_TIMEOUT

        if reset:
            self.reset()

    def reset(self):
        self.setSwitches(tuple(False * 10))

    def setSwitch(self, index: int, value: bool = False) -> None:
        if index < 1 or index > 10:
            raise ValueError("AttenuatorSwitchController.setSwitch: index out of range (1..10)")
        if index == 10:
            index = 0
        cmd = "A" if value else "B"
        self.inst.write(f"{cmd}{index}")

    def setSwitches(self, values: Sequence[bool]) -> None:
        if len(values) < 8 or len(values) > 10:
            raise ValueError("AttenuatorSwitchController.setSwitches: values must be a sequence of 8 to 10 bool")
        
        cmd = ""
        for i in range(len(values)):
            cmd += "A" if values[i] else "B"
            cmd += str((i + 1) % 10)   # convert 0..9 to 1..0
        self.inst.write(cmd)

        