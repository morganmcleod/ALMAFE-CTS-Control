from .Interface import PowerDetect_Interface, DetectMode
from INSTR.PNA.PNAInterface import PNAInterface
from INSTR.PNA.AgilentPNA import FAST_CONFIG, DEFAULT_POWER_CONFIG

class PDPNA(PowerDetect_Interface):

    def __init__(self, pna: PNAInterface):
        self.pna = pna
        self.reset()

    def reset(self):
        self._detect_mode = DetectMode.SPEC_AN
    
    def configure(self, **kwargs) -> None:
        config = kwargs.get('config', None)
        if config is not None:
            self.pna.setMeasConfig(config)
        power_config = kwargs.get('power_config', None)
        if power_config is not None:
            self.pna.setPowerConfig(power_config)

    @property
    def detect_mode(self) -> DetectMode:
        return self._detect_mode
    
    @detect_mode.setter
    def detect_mode(self, mode: DetectMode):
        self._detect_mode = mode

    def read(self, **kwargs) -> float | tuple[list[float], list[float]]:
        if self._detect_mode == DetectMode.METER:
            amp, _ = self.pna.getAmpPhase()
            return amp
        if self._detect_mode == DetectMode.SPEC_AN:
            amps, _ = self.pna.getTrace()
            return [], amps
        
