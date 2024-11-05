from .Interface import PowerDetect_Interface, DeviceInfo, DetectMode, Units
from INSTR.PowerMeter.KeysightE441X import PowerMeter
from DebugOptions import *

class PDPowerMeter(PowerDetect_Interface):

    def __init__(self, powerMeter: PowerMeter):
        self.powerMeter = powerMeter
        self.reset()
    
    def reset(self):
        self.powerMeter.reset()
        self._fast_mode = False
        self._units = Units.DBM

    def configure(self, **kwargs) -> None:
        units = kwargs.get('units', None)
        if units is not None:
            self.units = units
        fast_mode = kwargs.get('fast_mode', False)        
        self.powerMeter.setFastMode(fast_mode)
        averaging = kwargs.get('averaging', False)
        if averaging:
            self.powerMeter.enableAveraging()
        self.powerMeter.initContinuous()

    @property
    def device_info(self) -> DeviceInfo:
        if SIMULATE:
            return DeviceInfo(
                name = 'Power detect',
                resource = 'simulated power meter',
                connected = True
            )
        else:
            deviceInfo = DeviceInfo.parse_obj(self.powerMeter.deviceInfo())
            deviceInfo.name = "Power detect"
            return deviceInfo

    @property
    def detect_mode(self) -> DetectMode:
        return DetectMode.METER

    @property
    def units(self) -> Units:
        return self._units
    
    @units.setter
    def units(self, units: Units | str) -> None:
        if isinstance(units, str):
            units = Units(units)        
        if isinstance(units, Units):
            self.powerMeter.setUnits(units)
            self._units = units

    def read(self, **kwargs) -> float:
        mode = kwargs.get('mode', None)
        if mode == 'auto':
            return self.powerMeter.autoRead()
        else:
            averaging = kwargs.get('averaging', 1)            
            return self.powerMeter.read(averaging = averaging)
    
    def zero(self) -> None:
        self.powerMeter.zero()
