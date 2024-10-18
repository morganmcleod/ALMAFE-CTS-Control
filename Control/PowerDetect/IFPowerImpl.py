from .Interface import PowerDetect_Interface
from AMB.CCADevice import IFPowerInterface

class IFPowerImpl(IFPowerInterface):
    def __init__(self, powerDetect: PowerDetect_Interface):
        self.powerDetect = powerDetect

    def read(self, **kwargs) -> float:
        return self.powerDetect.read(**kwargs)
