from CTSDevices.Common.RemoveDelims import removeDelims   #todo move Common out of CTSDevices
import pyvisa
import re
import logging

class PowerSupplySimulator():
    
    def __init__(self):
        self.voltage = {}
        self.current = {}
    
    def idQuery(self) -> bool:
        self.mfr = ""
        self.model = "Power supply simulator"
    
    def reset(self):
        return True
        
    def errorQuery(self):
        """Send an error query and return the results

        :return (int, str): Error code and string
        """
        return 0, ""

    def setVoltage(self, voltage: float = 0, channel: int = 1) -> None:
        self.voltage[channel] = voltage
        self.current[channel] = voltage / 10

    def setCurrentLimit(self, limit:float = 0, channel: int = 1):
        pass

    def setOutputEnable(self, enable: bool = False):
        pass

    def getVoltage(self, channel: int = 1) -> float:
        return self.voltage[channel]

    def getCurrent(self, channel: int = 1) -> float:
        return self.current[channel]
