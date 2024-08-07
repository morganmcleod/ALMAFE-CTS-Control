from .Interface import PowerDetect_Interface, DeviceInfo, DetectMode, Units
from INSTR.DMM.HP34401 import HP34401, Function, AutoZero
from DebugOptions import *

class PDVoltMeter(PowerDetect_Interface):

    def __init__(self, voltMeter: HP34401):
        self.voltMeter = voltMeter
        self.reset()

    def reset(self):
        self._detect_mode = DetectMode.VOLT_METER
        self._units = Units.VOLTS
    
    def configure(self, **kwargs) -> None:
        self.voltMeter.configureMeasurement(Function.DC_VOLTAGE)
        self.voltMeter.configureAutoZero(AutoZero.OFF)
        self.voltMeter.configureAveraging(Function.DC_VOLTAGE, 1)
    
    @property
    def device_info(self) -> DeviceInfo:
        if SIMULATE:
            return DeviceInfo(
                name = 'Power detect',
                resource = 'simulated volt meter',
                connected = True
            )
        else:
            deviceInfo = DeviceInfo.parse_obj(self.voltMeter.deviceInfo)
            deviceInfo.name = "Power detect"
            return deviceInfo
    
    @property
    def detect_mode(self) -> DetectMode:
        return self._detect_mode

    @property
    def units(self) -> Units:
        return self._units
    
    @units.setter
    def units(self, units: Units) -> None:
        self._units = units

    def read(self, **kwargs) -> float | tuple[list[float], list[float]]:
        return self.voltMeter.readSinglePoint()
        
    def zero(self) -> None:
        pass