import pyvisa
from typing import Any
import logging

class VisaInstrument():
    def __init__(self,
            resource_name: str,
            max_errors: int = 5,            
            **kwargs: Any):
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        rm = pyvisa.ResourceManager()
        self.resource_name = resource_name
        try:
            self.inst = rm.open_resource(resource_name, **kwargs)
            self.connected = True
        except Exception as e:
            print(e)
            self.logger.error(e)
            self.inst = None
            self.connected = False
        self.max_errors = max_errors
        self.errors_countdown = max_errors

    def close(self):
        self.inst.close()

    def write(self, message: str, termination: str | None = None, encoding: str | None = None) -> int:
        if not self.connected:
            return 0
        try:
            self.inst.write(message, termination, encoding)
        except:
            return self.__count_error()
            return 0

    def query(self, message: str, delay: float | None = None, return_on_error: str | None = None) -> str:
        if not self.connected:
            return return_on_error
        try:
            return self.inst.query(message, delay)
        except:
            return self.__count_error()
                
    def read(self, termination: str | None = None, encoding: str | None = None, return_on_error: str | None = None) -> str:
        if not self.connected:
            return return_on_error
        try:
            return self.inst.read(termination, encoding)
        except:
            self.__count_error()            
            return return_on_error

    def __count_error(self):
        self.errors_countdown -= 1
        if self.errors_countdown == 0:
            self.logger.error(f"VisaInstrument {self.resource_name} stopping: too many errors ({self.max_errors}).")
            self.connected = False
