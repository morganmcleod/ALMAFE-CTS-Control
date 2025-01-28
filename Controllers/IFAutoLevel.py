
import time
import logging
import yaml
from math import floor
from pydantic import BaseModel
from Controllers.IFSystem.Interface import IFSystem_Interface, InputSelect
from Controllers.PowerDetect.Interface import PowerDetect_Interface, DetectMode
from INSTR.Chopper.Interface import Chopper_Interface
from simple_pid import PID

class IFAutoLevelSettings(BaseModel):
    Kp: float = 1
    Ki: float = 0
    Kd: float = 0
    min_atten: int = 0
    max_atten: int = 121
    max_iter: int = 15
    tolerance: float = 0.75   # dB
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
            inputSelect: InputSelect = InputSelect.POL0_USB
        ) -> tuple[bool, str]:
        
        if self.powerDetect.detect_mode == DetectMode.SPEC_AN:
            # nothing to do in this mode
            return True, ""

        self.powerDetect.configure(units = 'dBm')
        self.ifSystem.input_select = inputSelect
        self.chopper.stop()
        self.chopper.gotoHot()

        self.loadSettings()
        output = self.ifSystem.attenuation
        pid = PID(-self.settings.Kp, -self.settings.Ki, -self.settings.Kd, starting_output = output)
        pid.setpoint = targetLevel
        pid.output_limits = (self.settings.min_atten, self.settings.max_atten)
        pid.sample_time = self.settings.sleep - 0.1

        done = error = False
        msg = ""

        amp = self.powerDetect.read(averaging = 10)
        if not amp:
            error = True

        iter = 0
        while not done and not error: 
            self.logger.info(f"IF autoLevel: iter={iter}, amp={amp:.1f} dBm, atten={int(round(output))} dB")
            output = pid(amp)
            self.ifSystem.attenuation = int(round(output))
            time.sleep(self.settings.sleep)
            amp = self.powerDetect.read(averaging = 10)
            
            iter += 1
            if targetLevel - self.settings.tolerance <= amp <= targetLevel + self.settings.tolerance:
                done = True
                msg = f"IF autoLevel SUCCESS: iter={iter}, amp={amp:.1f} dBm, atten={int(round(output))} dB"
            elif iter > self.settings.max_iter:
                error = True
                msg = f"IF autoLevel FAIL: iter={iter}, amp={amp:.1f} dBm, atten={int(round(output))} dB"

        if error:
            self.logger.error(msg)
            return error, msg
        elif msg:
            self.logger.info(msg)
            return True, ""
