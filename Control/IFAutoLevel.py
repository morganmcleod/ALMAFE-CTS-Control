
import time
import logging
import yaml
from math import floor
from pydantic import BaseModel
from Control.IFSystem.Interface import IFSystem_Interface, InputSelect
from Control.PowerDetect.Interface import PowerDetect_Interface, DetectMode
from INSTR.Chopper.Interface import Chopper_Interface
from Control.PBAController import PBAController

class IFAutoLevelSettings(BaseModel):
    min_atten: int = 0
    max_atten: int = 121
    max_iter: int = 15
    tolerance: float = 0.5   # dB
    sleep: float = 0.25

class IFAutoLevel():
    SETTINGS_FILE = "Settings/Settings_IFAutoLevel.yaml"

    def __init__(self, 
            ifSystem: IFSystem_Interface, 
            powerDetect: PowerDetect_Interface,
            chopper: Chopper_Interface):
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.ifSystem = ifSystem
        self.powerDetect = powerDetect
        self.chopper = chopper
        self.loadSettings()
        self.controller = PBAController(
            tolerance = self.settings.tolerance,
            output_limits = (self.settings.min_atten, self.settings.max_atten),
            min_resolution = 1,
            max_iter = self.settings.max_iter
        )

    def loadSettings(self):
        try:
            with open(self.SETTINGS_FILE, "r") as f:
                d = yaml.safe_load(f)
                self.settings = IFAutoLevelSettings.parse_obj(d)
        except:
            self.settings = IFAutoLevelSettings()
            self.saveSettings()

    def saveSettings(self):
        with open(self.SETTINGS_FILE, "w") as f:
            yaml.dump(self.settings.dict(), f)

    def autoLevel(self, 
            targetLevel: float, 
            inputSelect: InputSelect = InputSelect.POL0_USB) -> tuple[bool, str]:
        
        if self.powerDetect.detect_mode == DetectMode.SPEC_AN:
            # nothing to do in this mode
            return True, ""

        self.loadSettings()
        self.controller.reset()
        self.controller.setpoint = targetLevel

        self.powerDetect.configure(units = 'DBM')
        self.ifSystem.input_select = inputSelect
        self.chopper.stop()
        self.chopper.gotoHot()       
        
        setValue = int(self.settings.max_atten - floor(self.controller.output))
        self.ifSystem.attenuation = setValue
        time.sleep(self.settings.sleep)
        amp = self.powerDetect.read(averaging = 10)

        done = error = False
        msg = ""

        if not amp:
            error = True
        
        while not done and not error: 
            self.logger.info(f"IF autoLevel: iter={self.controller.iter} amp={amp:.1f} dBm setValue={setValue} dB")
            setValue = setValue = int(self.settings.max_atten - floor(self.controller.process(amp)))
            if self.controller.done and not self.controller.fail:
                msg = f"IF autoLevel: success iter={self.controller.iter} amp={amp:.1f} dBm setValue={setValue} dB"
                done = True
            elif self.controller.fail:
                msg = f"IF autoLevel: fail iter={self.controller.iter} max_iter={self.settings.max_iter} setValue={setValue} dB"
                error = True
            else:
                self.ifSystem.attenuation = setValue
                time.sleep(0.25)
                amp = self.powerDetect.read(averaging = 10)
                if amp is None:
                    error = True
                    msg = f"IF autoLevel: powerDetect.read error at iter={self.controller.iter}."

        if error:
            self.logger.error(msg)
            return error, msg
        elif msg:
            self.logger.info(msg)
            return True, ""
