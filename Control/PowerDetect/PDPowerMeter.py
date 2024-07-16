from .Interface import PowerDetect_Interface, DetectMode
from INSTR.PowerMeter.KeysightE441X import PowerMeter, Unit

class PDPowerMeter(PowerDetect_Interface):

    def __init__(self, powerMeter: PowerMeter):
        self.powerMeter = powerMeter
        self.reset()
    
    def reset(self):
        self.powerMeter.reset()
        self._fast_mode = False

    def configure(self, **kwargs) -> None:
        units = kwargs.get('units', None)
        fast_mode = kwargs.get('fast_mode', False)
        if isinstance(units, str):
            units = Unit(units)
        if isinstance(units, Unit):
            self.powerMeter.setUnits(units)
        self.powerMeter.setFastMode(fast_mode)

    @property
    def detect_mode(self) -> DetectMode:
        return DetectMode.METER

    def read(self, **kwargs) -> float:
        mode = kwargs.get('mode', None)
        if mode == 'auto':
            return self.powerMeter.autoRead()
        else:
            averaging = kwargs.get('averaging', 1)
            return self.powerMeter.read(averaging = averaging)
    
    def zero(self) -> None:
        self.powerMeter.zero()
