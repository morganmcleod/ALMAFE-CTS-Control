from pydantic import BaseModel
from typing import List, Optional
from enum import Enum
import pyvisa

class TaskType(Enum):
    STATIC = 0
    DIGITAL = 1

class DigitalPort(Enum):
    LOW_ORDER_8BIT = 0
    HIGH_ORDER_8BIT = 1
    WORD_16BIT = 2

class DigitalMethod(Enum):
    BINARY = 0
    ASCII = 1

class SwitchConfig(BaseModel):
    taskType: TaskType = TaskType.STATIC
    slot: int = 0
    port: DigitalPort = DigitalPort.LOW_ORDER_8BIT
    method: DigitalMethod = DigitalMethod.BINARY
    dataStream: int = 1

class SwitchController():
    """The HP3488a switch controller"""
    
    DEFAULT_TIMEOUT = 15000     # milliseconds
    
    def __init__(self, resource="GPIB0::9::INSTR", reset=True):
        """Constructor

        :param str resource: VISA resource string, defaults to "GPIB0::13::INSTR"
        :param bool reset: If true, reset the instrument and set default configuration, defaults to True
        """
        rm = pyvisa.ResourceManager()
        self.inst = rm.open_resource(resource)
        self.inst.timeout = self.DEFAULT_TIMEOUT
        self.readConfig = SwitchConfig()
        self.writeConfig = SwitchConfig()

    def staticRead(self) -> int:
        result = self.inst.query(f"SREAD {self.readConfig.slot}04")
        return int(result.strip())
    
    def staticWrite(self, data:int) -> None:
        self.inst.write(f"SWRITE {self.writeConfig.slot}00, {data}")

    def digitalRead(self, numReadings: int = 1) -> List[int]:
        cmd = "DBR" if self.readConfig.method == DigitalMethod.BINARY else "DREAD"
        result = self.inst.query(f"{cmd} {self.readConfig.slot}0{self.readConfig.port.value}, {numReadings}")
        result = result.split(',')
        return [int(i) for i in result]
    
    def digitalWrite(self, data: List[int]) -> None:
        cmd = "DBW" if self.writeConfig.method == DigitalMethod.BINARY else "DWRITE"
        cmd = f"{cmd} {self.writeConfig.slot}0{self.writeConfig.port.value}, {','.join(data)}"
        self.inst.write(cmd)
