from .Interface import PowerDetect_Interface, DeviceInfo, DetectMode, Units
from INSTR.DMM.HP34401 import HP34401, Function, AutoZero, TriggerSource
from DebugOptions import *

class PDVoltMeter(PowerDetect_Interface):

    def __init__(self, voltMeter: HP34401):
        self.voltMeter = voltMeter
        self.reset()

    def reset(self):
        self._detect_mode = DetectMode.VOLT_METER
        self._units = Units.VOLTS
        self._last_read = None
    
    def configure(self, **kwargs) -> None:
        self.voltMeter.configureMeasurement(
            Function.DC_VOLTAGE, 
            autoRange = False, 
            manualRange = 0.1
        )
        self.voltMeter.configureAutoZero(AutoZero.OFF)
        self.voltMeter.configureAveraging(Function.DC_VOLTAGE, 1)
        sample_count = kwargs.get('sample_count', 1)
        if sample_count > 1:
            self.voltMeter.inst.write(f"SAMP:COUN {sample_count};")
        self.voltMeter.configureTrigger(TriggerSource.IMMEDIATE)
    
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

    def read(self, **kwargs) -> list[float]:
        self._last_read = self.voltMeter.read()
        return self._last_read
        
    @property
    def last_read(self) -> list[float]:
        return self._last_read
    
    def zero(self) -> None:
        pass