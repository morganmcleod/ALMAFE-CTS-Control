import logging
import time
import threading
import yaml
from pydantic import BaseModel
from simple_pid import PID
from app_Common.CTSDB import CTSDB
from .Interface import RFSource_Interface, AutoRFStatus
from Controllers.PowerDetect.Interface import PowerDetect_Interface
from Controllers.schemas.DeviceInfo import DeviceInfo
from Controllers.schemas.LO import LOSettings
from AMB.AMBConnectionItf import AMBConnectionItf
from AMB.LODevice import LODevice
from AMB.FEMCDevice import FEMCDevice
from DBBand6Cart.WCAs import WCA, WCAs
from INSTR.SignalGenerator.Interface import SignalGenInterface

class PIDSettings(BaseModel):
    P: float = 0.2
    I: float = 3.5
    D: float = 0
    maxIter: int = 15
    tolerance: float = 0.75 # dB
    iterSleep: float = 0.2

class SidebandSourceSettings(BaseModel):
    wcaConfig: WCA = WCA()
    loSettings: LOSettings = LOSettings(setReference = True, refAmplitude = 15)
    autoRFSettings: PIDSettings = PIDSettings()
    
class SidebandSource(RFSource_Interface):

    RFSRC_SETTINGS = "Settings/Settings_SidebandSource.yaml"

    def __init__(self,
            conn: AMBConnectionItf,
            refSynth: SignalGenInterface,
            nodeAddr: int = 0x13,
            femcPort: int = FEMCDevice.PORT_BAND7,
            polarization: int = 0
        ):
        self.conn = conn
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.loDevice = LODevice(conn, nodeAddr, band = 6, femcPort = femcPort)
        self.refSynth = refSynth
        self.polarization = polarization
        self.autoRFStatus = AutoRFStatus(
            last_output = 15
        )
        self.pid = None
        self.coldMultiplier = LODevice.COLD_MULTIPLIERS[self.loDevice.band]
        self.warmMultiplier = LODevice.WARM_MULTIPLIERS[self.loDevice.band]        
        self.loadSettings()
        self.pll = {
            'loFreqGHz': 0, 
            'courseTune': 0, 
            'temperature': 0, 
            'nullPLL': False,
            'lockVoltage': False, 
            'unlockDetected': False, 
            'refTP': 0, 
            'IFTP': 0, 
            'corrV': 0, 
            'isLocked': False
        }

    def loadSettings(self):
        try:
            with open(self.RFSRC_SETTINGS, "r") as f:
                d = yaml.safe_load(f)
                self.config = SidebandSourceSettings.model_validate(d)
                if self.config.wcaConfig.serialNum:
                    DB = WCAs(driver = CTSDB())
                    configs = DB.read(serialNum = self.config.wcaConfig.serialNum)
                    if configs:
                        self.setConfig(configs[0].key)
        
        except:
            self.config = SidebandSourceSettings()
            self.saveSettings()

    def saveSettings(self):
        with open(self.RFSRC_SETTINGS, "w") as f:
            yaml.dump(self.config.model_dump(), f)

    def getDeviceInfo(self) -> DeviceInfo:        
        return DeviceInfo(
            name = "MTS2 RF Source",
            resource = f"{self.conn.getChannel()}",
            connected = self.conn.connected()
        )

    def setConfig(self, configId:int) -> bool:
        DB = WCAs(driver = CTSDB())
        self.config.wcaConfig = WCA()
        if configId == 0:
            self.saveSettings()
            return True
        configs = DB.read(configId)
        if not configs:
            return False
        self.config.wcaConfig = configs[0]
        self.saveSettings()
        self.loDevice.setPABias(0, gateVoltage = self.config.wcaConfig.VGp0)
        self.loDevice.setPABias(1, gateVoltage = self.config.wcaConfig.VGp1)

    def getConfig(self) -> int:
        return self.config.wcaConfig.key if self.config is not None else 0

    def setFrequency(self, 
             freqGHz: float,
             settings: LOSettings = None
        ) -> tuple[bool, str]:
        if settings is None:
            settings = self.config.loSettings
        if not self.refSynth.setFrequency(freqGHz / self.coldMultiplier / self.warmMultiplier):
            return False, "SidebandSource.setFrequency: error setting synthesizer frequency"
        if not self.refSynth.setAmplitude(settings.refAmplitude):
            return False, "SidebandSource.setFrequency: error setting synthesizer amplitude"
        if not self.refSynth.setRFOutput(True):
            return False, "SidebandSource.setFrequency: error enabling synthesizer output"
        self.pll['loFreqGHz'] = freqGHz
        self.pll['isLocked'] = True        
        return True, ""
    
    def setOutputPower(self, percent: float) -> tuple[bool, str]:
        paGateVolts = self.config.wcaConfig.VGp1 if self.polarization == 1 else self.config.wcaConfig.VGp0
        self.loDevice.setPABias(self.polarization, 2.5 * percent / 100, paGateVolts)
        if percent > 0:
            self.autoRFStatus.last_output = percent
        return True, ""
        
    def getPAVD(self) -> float:
        pa = self.loDevice.getPA()
        if self.polarization == 0:
            return pa['VDp0']
        elif self.polarization == 1:
            return pa['VDp1']
    
    def getPLL(self) -> dict:
        return self.pll

    def getAutoRFStatus(self) -> AutoRFStatus:
        return self.autoRFStatus

    def autoRFPower(self, 
            powerDetect: PowerDetect_Interface, 
            targetSBPower: float,
            reinitialize: bool = False,
            **kwargs
        ) -> tuple[bool, str]:
        if kwargs.get('on_thread', False):
            threading.Thread(target = self._autoRFPower, args = (powerDetect, targetSBPower, reinitialize), daemon = True).start()
            return True, ""
        else:
            return self._autoRFPower(powerDetect, targetSBPower, reinitialize)

    def _autoRFPower(self, 
            powerDetect: PowerDetect_Interface, 
            targetSBPower: float,
            reinitialize: bool = False
        ) -> tuple[bool, str]:

        self.loadSettings()
        self.autoRFStatus.is_active = True
        self.setOutputPower(self.autoRFStatus.last_output)
        time.sleep(self.config.autoRFSettings.iterSleep)
        
        self.pid = PID(
            self.config.autoRFSettings.P, 
            self.config.autoRFSettings.I, 
            self.config.autoRFSettings.D,
            output_limits = (0, 100),
            starting_output = self.autoRFStatus.last_output,
            setpoint = targetSBPower
        )

        self.autoRFStatus.last_measured = powerDetect.read()
        self.logger.info(f"SidebandSource.autoRFPower: target:{targetSBPower} dBm, powerLevel:{self.autoRFStatus.last_measured} dBm, reinitialize:{reinitialize}")

        success = False
        error = False
        maxIter = self.config.autoRFSettings.maxIter
        iter = 0
        control = None
        tolerance = self.config.autoRFSettings.tolerance

        while not success and not error:
            iter += 1
            self.autoRFStatus.last_output = control
            control = self.pid(self.autoRFStatus.last_measured)
            if control == self.autoRFStatus.last_output == 100:
                error = True
                msg = f"SidebandSource.autoRFPower: AT MAXIMUM iter:{iter} control:{control:.2f} %, powerLevel:{self.autoRFStatus.last_measured} dBm"
                self.logger.warning(msg)
            elif iter >= maxIter:
                error = True
                msg = f"SidebandSource.autoRFPower: FAILED in {maxIter} iterations: control:{control:.2f} %, powerLevel:{self.autoRFStatus.last_measured} dBm"
                self.logger.warning(msg)
            else:
                self.setOutputPower(control)
                time.sleep(self.config.autoRFSettings.iterSleep)
                self.autoRFStatus.last_measured = powerDetect.read()
                if abs(self.autoRFStatus.last_measured - targetSBPower) < tolerance:
                    success = True
                msg = f"SidebandSource.autoRFPower: iter:{iter} control:{control:.2f} %, powerLevel:{self.autoRFStatus.last_measured} dBm"
                self.logger.info(msg)

        self.autoRFStatus.is_active = False
        return success, msg
