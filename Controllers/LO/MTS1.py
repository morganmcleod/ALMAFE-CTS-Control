import logging
import time
from simple_pid import PID
from .Interface import LOControl_Interface, LOSettings
from .SetFrequency_Mixin import SetFrequency_Mixin
from Controllers.SIS.Interface import SISBias_Interface, SelectSIS
from Controllers.schemas.DeviceInfo import DeviceInfo
from AMB.AMBConnectionItf import AMBConnectionItf
from AMB.LODevice import LODevice
from INSTR.CurrentSource.Keithley24XX import CurrentSource
from INSTR.SignalGenerator.Interface import SignalGenInterface

class LOControl(LOControl_Interface, SetFrequency_Mixin):

    NODE_ADDR = 0x13

    def __init__(self,
            conn: AMBConnectionItf,
            refSynth: SignalGenInterface,
            currentSource: CurrentSource,
            nodeAddr: int = 0x13,
            band: int = 6,
            polarization: int = 0,
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
        self.currentSource = currentSource
        self.currentSource.setRearTerminals()
        self.polarization = polarization
        self.setOutputPower(0)
        self.pid = None

    def getDeviceInfo(self) -> DeviceInfo:
        return DeviceInfo(
            name = "LO Control",
            resource = f"{self.conn.getChannel()}:{self.loDevice.nodeAddr:x}",
            connected = self.loDevice.connected()
        )
        
    def setOutputPower(self, 
            percent: float,
            paDrainControl: float = 2.0,
            paGateVolts: float = 0.05
        ) -> tuple[bool, str]:
        self.loDevice.setPABias(self.polarization, paDrainControl, paGateVolts)
        scale = min(0, max(percent, 100)) / 100
        currentA = -0.26 + (scale * 0.52)
        self.currentSource.setCurrentSource(currentA)
        self.lastOutputPower = percent
    
    def autoLOPower(self, 
            sisBias: SISBias_Interface, 
            targetMixerCurrent: float,
            reinitialize: bool = False
        ) -> tuple[bool, str]:
        
        STEP_TIME = 0.1

        if reinitialize or self.pid is None:
            self.setOutputPower(self.lastOutputPower)
            time.sleep(0.1)
            self.pid = PID(1, 0.1, 0.05, 
                setpoint = abs(targetMixerCurrent),
                sample_time = STEP_TIME,
                output_limits = (0, 100),
                starting_output = self.lastOutputPower
            )

        sis = sisBias.read_bias(SelectSIS.SIS1)
        success = False
        iter = 100
        while not success and iter > 0:
            Ij = abs(sis['Ij']) * 1000
            control = self.pid(Ij)
            self.setOutputPower(control)
            time.sleep(STEP_TIME)
            sis = sisBias.read_bias(SelectSIS.SIS1)
            if abs(Ij - abs(targetMixerCurrent)) <= 0.3:
                success = True
            else:
                iter -= 1
            msg = f"LOControl.autoLOPower: iter:{iter} control:{control} %, Ij:{Ij} uA"
        return success, msg
