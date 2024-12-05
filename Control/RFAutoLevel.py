import time
import logging
import yaml
from pydantic import BaseModel
from Control.RFSource import RFSource
from Control.IFSystem.Interface import IFSystem_Interface
from Control.PowerDetect.Interface import PowerDetect_Interface
from Control.PBAController import PBAController

class RFAutoLevelSettings(BaseModel):
    min_percent: int = 15
    max_percent: int = 100    
    max_iter: int = 15
    tolerance: float = 0.5   # dB
    sleep: float = 0.2

class RFAutoLevel():
    SETTINGS_FILE = "Settings/Settings_RFAutoLevel.yaml"

    def __init__(self,
            ifSystem: IFSystem_Interface,
            powerDetect: PowerDetect_Interface,
            rfSrcDevice: RFSource):
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.ifSystem = ifSystem
        self.powerDetect = powerDetect
        self.rfSrcDevice = rfSrcDevice
        self.loadSettings()
        self.controller = PBAController(
            tolerance = self.settings.tolerance,
            output_limits = (self.settings.min_percent, self.settings.max_percent),
            min_resolution = 0.01,
            max_iter = self.settings.max_iter
        )
        
    def loadSettings(self):
        try:
            with open(self.SETTINGS_FILE, "r") as f:
                d = yaml.safe_load(f)
                self.settings = RFAutoLevelSettings.parse_obj(d)
        except:
            self.settings = RFAutoLevelSettings()
            self.saveSettings()

    def saveSettings(self):
        with open(self.SETTINGS_FILE, "w") as f:
            yaml.dump(self.settings.dict(), f)

    def autoLevel(self, 
            freqIF: float, 
            targetLevel: float,
            powerDetect: PowerDetect_Interface = None
        ) -> tuple[bool, str]:

        if not powerDetect:
            powerDetect = self.powerDetect

        self.loadSettings()
        self.controller.reset()
        self.controller.setpoint = targetLevel        
        self.ifSystem.frequency = freqIF
        
        self.rfSrcDevice.setPAOutput(self.rfSrcDevice.paPol, self.controller.output)
        time.sleep(self.settings.sleep)
        amp = powerDetect.read()
        
        done = error = False
        msg = ""

        if not amp:
            error = True
        
        while not done and not error: 
            self.logger.info(f"RF autoLevel: iter={self.controller.iter} setValue={self.controller.output:.2f}% amp={amp:.1f} dBm")
            setValue = self.controller.process(amp)
            if self.controller.done and not self.controller.fail:
                msg = f"RF autoLevel: success amp={amp:.1f} dBm"
                done = True
            elif self.controller.fail:
                msg = f"RF autoLevel: fail iter={self.controller.iter} max_iter={self.settings.max_iter} setValue={self.controller.output:.2f}%"
                error = True
            else:
                self.rfSrcDevice.setPAOutput(self.rfSrcDevice.paPol, setValue)
                time.sleep(self.settings.sleep)
                amp = powerDetect.read(averaging = 1, delay = 0)
                if amp is None:
                    error = True
                    msg = f"RF autoLevel: powerDetect.read error at iter={self.controller.iter}."
            
        if error:
            self.logger.error(msg)
            return error, msg
        elif msg:
            self.logger.info(msg)
            return True, ""

    @property
    def last_read(self) -> float:
        return self.powerDetect.last_read
