from pydantic import BaseModel
from typing import List
from enum import Enum
import logging
from CTSDevices.Common.VisaInstrument import VisaInstrument

class DigitalPort(Enum):
    LOW_ORDER_8BIT = 0
    HIGH_ORDER_8BIT = 1
    WORD_16BIT = 2

class DigitalMethod(Enum):
    BINARY = 0
    ASCII = 1

class SwitchConfig(BaseModel):
    slot: int = 0
    port: DigitalPort = DigitalPort.LOW_ORDER_8BIT
    method: DigitalMethod = DigitalMethod.BINARY

class SwitchController():
    """The HP3488a switch controller"""
    
    DEFAULT_TIMEOUT = 15000     # milliseconds
    
    def __init__(self, resource: bool = "GPIB0::9::INSTR", reset: bool = True, 
                 readConfig: SwitchConfig = None, writeConfig: SwitchConfig = None):
        """Constructor

        :param str resource: VISA resource string, defaults to "GPIB0::13::INSTR"
        :param bool reset: If true, reset the instrument and set default configuration, defaults to True
        """
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.connected = False
        self.inst = VisaInstrument(resource, timeout = self.DEFAULT_TIMEOUT)
        if readConfig:
            self.readConfig = readConfig
        if writeConfig:
            self.writeConfig = writeConfig
        if reset:
            self.reset()

    def reset(self) -> None:
        self.inst.write("CRESET 1, 2, 3")

    def isConnected(self) -> bool:
        return self.inst.connected and self.connected

    def staticRead(self) -> int:
        try:
            result = self.inst.query(f"SREAD {self.readConfig.slot}04")
            return int(result.strip())
        except:
            self.logger.error("Not connected to HP3488a switch controller")
            self.connected = False
    
    def staticWrite(self, data:int) -> None:
        try:
            self.inst.write(f"SWRITE {self.writeConfig.slot}00, {data}")
        except:
            self.logger.error("Not connected to HP3488a switch controller")
            self.connected = False            

    def digitalRead(self, numReadings: int = 1) -> List[int]:
        try:
            cmd = "DBR" if self.readConfig.method == DigitalMethod.BINARY else "DREAD"
            result = self.inst.query(f"{cmd} {self.readConfig.slot}0{self.readConfig.port.value}, {numReadings}")
            result = result.split(',')
            return [int(i) for i in result]
        except:
            self.logger.error("Not connected to HP3488a switch controller")
            self.connected = False
    
    def digitalWrite(self, data: List[int]) -> None:
        try:
            cmd = "DBW" if self.writeConfig.method == DigitalMethod.BINARY else "DWRITE"
            cmd = f"{cmd} {self.writeConfig.slot}0{self.writeConfig.port.value},{','.join(list(map(str, data)))}"
            self.inst.write(cmd)
        except:
            self.logger.error("Not connected to HP3488a switch controller")
            self.connected = False            
