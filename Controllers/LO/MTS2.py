import logging
import time
import yaml
from pydantic import BaseModel
from simple_pid import PID
from .Interface import LOControl_Interface, AutoLOStatus
from .SetFrequency_Mixin import SetFrequency_Mixin
from Controllers.SIS.Interface import SISBias_Interface, SelectSIS
from Controllers.schemas.DeviceInfo import DeviceInfo
from AMB.AMBConnectionItf import AMBConnectionItf
from AMB.LODevice import LODevice
from INSTR.SignalGenerator.Interface import SignalGenInterface

class PIDSettings(BaseModel):
    P: float = 0.2
    I: float = 1.2
    D: float = 0
    maxIter: int = 15
    tolerance: float = 0.5  # uA
    iterSleep: float = 0.2

class LOControl(LOControl_Interface, SetFrequency_Mixin):

    LOCONTROL_SETTINGS = "Settings/Settings_LOControl.yaml"

    def __init__(self,
            conn: AMBConnectionItf,
            refSynth: SignalGenInterface,
            nodeAddr: int = 0x13,
            band: int = 6,
            polarization: int = 1,
            ytoLowGHz: float = 12.22,
            ytoHighGHz: float = 14.77
        ):
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.conn = conn
        self.loDevice = LODevice(conn, nodeAddr, band = band, femcPort = band)
        self.refSynth = refSynth
        SetFrequency_Mixin.__init__(self,
            self.loDevice, 
            self.refSynth, 
            LODevice.COLD_MULTIPLIERS[self.loDevice.band],
            LODevice.WARM_MULTIPLIERS[self.loDevice.band]
        )
        self.loDevice.setYTOLimits(ytoLowGHz, ytoHighGHz)
        self.polarization = polarization
        self.pid = None
        self.setOutputPower(0)
        self.autoLOStatus = AutoLOStatus(
            last_output = 15
        )
        self.loadSettings()

    def loadSettings(self):
        try:
            with open(self.LOCONTROL_SETTINGS, "r") as f:
                d = yaml.safe_load(f)
                self.config = PIDSettings.model_validate(d)
        
        except:
            self.config = PIDSettings()
            self.saveSettings()

    def saveSettings(self):
        with open(self.LOCONTROL_SETTINGS, "w") as f:
            yaml.dump(self.config.model_dump(), f)

    def getDeviceInfo(self) -> DeviceInfo:
        return DeviceInfo(
            name = "LO Control",
            resource = f"{self.conn.getChannel()}:{self.loDevice.nodeAddr:x}",
            connected = self.loDevice.connected()
        )
    
    def getPLL(self) -> dict:
        return self.loDevice.getPLL()
    
    def getPA(self) -> dict:
        return self.loDevice.getPA()
    
    def setOutputPower(self, 
            percent: float,  
            paGateVolts: float = 0.05
        ) -> tuple[bool, str]:
        self.loDevice.setPABias(self.polarization, 2.5 * percent / 100, paGateVolts)
        if percent > 0:
            self.autoLOStatus.last_output = percent
    
    def getOuputPower(self) -> float:
        return self.autoLOStatus.last_output

    def getAutoLOStatus(self) -> AutoLOStatus:
        return self.autoLOStatus

    def autoLOPower(self, 
            sisBias: SISBias_Interface, 
            targetMixerCurrent: float,
            reinitialize: bool = False
        ) -> tuple[bool, str]:
        
        self.loadSettings()
        self.autoLOStatus.is_active = True
        self.setOutputPower(self.autoLOStatus.last_output)
        time.sleep(self.config.iterSleep)
        
        self.pid = PID(
            self.config.P, 
            self.config.I, 
            self.config.D,
            output_limits = (0, 100),
            starting_output = self.autoLOStatus.last_output,
            setpoint = abs(targetMixerCurrent)
        )

        sis = sisBias.read_bias(SelectSIS.SIS1)
        self.autoLOStatus.last_measured = abs(sis[1])
        self.logger.info(f"LOControl.autoLOPower: target:{targetMixerCurrent} uA, Ij:{self.autoLOStatus.last_measured:.2f} uA, reinitialize:{reinitialize}")
        
        success = False
        msg = ""
        error = False
        maxIter = self.config.maxIter
        iter = 0
        control = None
           
        while not success and not error:
            iter += 1
            control = self.pid(self.autoLOStatus.last_measured)
            self.autoLOStatus.last_output = control
            self.setOutputPower(control)
            sis = sisBias.read_bias(SelectSIS.SIS1)
            self.autoLOStatus.last_measured = abs(sis[1])
            msg = f"LOControl.autoLOPower: iter:{iter} control:{control:.2f} %, Ij:{self.autoLOStatus.last_measured:.2f} uA"
            self.logger.info(msg)
            if abs(self.autoLOStatus.last_measured - abs(targetMixerCurrent)) <= self.config.tolerance:
                success = True
            elif iter > maxIter or control == 100:
                error = True
                msg = f"LOControl.autoLOPower: FAILED in {iter} iterations: control:{control:.2f} %, Ij:{self.autoLOStatus.last_measured:.2f} uA"
                self.logger.warning(msg)
        
        self.autoLOStatus.is_active = False
        return success, msg
