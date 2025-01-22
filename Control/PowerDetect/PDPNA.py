import copy
from .Interface import PowerDetect_Interface, DeviceInfo, DetectMode, Units
from INSTR.PNA.PNAInterface import PNAInterface, TriggerSource
from INSTR.PNA.AgilentPNA import DEFAULT_CONFIG, DEFAULT_POWER_CONFIG
from DebugOptions import *

class PDPNA(PowerDetect_Interface):

    def __init__(self, pna: PNAInterface):
        self.pna = pna
        self.config = None
        self.reset()

    def reset(self):
        self._detect_mode = DetectMode.PNA
        self._last_read = None
        
    def configure(self, **kwargs) -> None:
        self.pna.reset()
        try:
            self.pna.workaroundPhaseLockLost()
        except:
            pass
        config = kwargs.get('config', DEFAULT_CONFIG)
        self.config = copy.copy(config)
        self.config.triggerSource = kwargs.get('trigger_source', TriggerSource.MANUAL)
        self.config.bandWidthHz = kwargs.get('bandwidth_hz', 35e3)
        self.pna.setMeasConfig(config)
        power_config = kwargs.get('power_config', DEFAULT_POWER_CONFIG)
        self.pna.setPowerConfig(power_config)

    @property
    def device_info(self) -> DeviceInfo:
        if SIMULATE:
            return DeviceInfo(
                name = 'Power detect',
                resource = 'simulated PNA',
                connected = True
            )
        else:
            deviceInfo = DeviceInfo.parse_obj(self.pna.deviceInfo())
            deviceInfo.name = "Power detect"            
            return deviceInfo

    @property
    def detect_mode(self) -> DetectMode:
        return self._detect_mode

    @property
    def units(self) -> Units:
        return Units.DB

    def read(self, **kwargs) -> float | tuple[float, float]:
        self.pna.initContinuous()
        self._last_read, phase = self.pna.getAmpPhase()
        if kwargs.get('amp_phase', False):
            return self._last_read, phase
        else:
            return self._last_read

    @property
    def last_read(self) -> float | tuple[float, float]:
        return self._last_read

    def zero(self) -> None:
        pass