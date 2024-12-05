from .Interface import PowerDetect_Interface
from AMB.CCADevice import IFPowerInterface

class IFPowerImpl(IFPowerInterface):
    def __init__(self, powerDetect: PowerDetect_Interface):
        self.powerDetect = powerDetect
        self._last_read = None

    def read(self, **kwargs) -> float:
        return self.powerDetect.read(**kwargs)
    
    @property
    def last_read(self) -> float:
        return self.powerDetect.last_read

