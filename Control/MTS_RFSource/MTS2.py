import typing
import time
from simple_pid import PID
import nidaqmx
from math import floor, ceil
from .Interface import SidebandSource_Interface
from ..PowerDetect.Interface import PowerDetect_Interface
from AMB.AMBConnectionItf import AMBConnectionItf
from AMB.LODevice import LODevice
from AMB.FEMCDevice import FEMCDevice
from INSTR.SignalGenerator.Keysight_PSG_MXG import SignalGenerator

class SidebandSource(SidebandSource_Interface):

    def __init__(self,
            conn: AMBConnectionItf,
            nodeAddr: int = 0x13,
            femcPort: int = FEMCDevice.PORT_BAND7,
            refSynthResource: str = "GPIB0::28::INSTR",
            polarization: int = 0
        ):
        self.loDevice = LODevice(conn, nodeAddr, band = 6, femcPort = femcPort)
        self.refSynth = SignalGenerator(refSynthResource)
        self.polarization = polarization
        self.freqGHz = 0
        self.lastOutputPower = 15
        self.pid = None
        self.coldMultiplier = LODevice.COLD_MULTIPLIERS[self.loDevice.band]
        self.warmMultiplier = LODevice.WARM_MULTIPLIERS[self.loDevice.band]

    def setFrequency(self, 
            freqGHz: float,
            refSynthAmplitude: float = 5,  # dBm
            paGateVolts: float = 0.10
        ) -> tuple[bool, str]:
        self.refSynth.setFrequency(freqGHz / self.coldMultiplier / self.warmMultiplier)
        self.refSynth.setAmplitude(refSynthAmplitude)
        self.refSynth.setRFOutput(True)
        self.setOutputPower(self.lastOutputPower, paGateVolts)
        self.freqGHz = freqGHz
        return True, ""
    
    def setOutputPower(self, 
            percent: float,            
            paGateVolts: float = 0.10
        ) -> tuple[bool, str]:
        self.loDevice.setPABias(self.polarization, 2.5 * percent / 100, paGateVolts)
        self.paGateVolts = paGateVolts
        self.lastOutputPower = percent
        return True, ""

    def getMonitorData(self) -> dict:
        return {
            'freqGHz': self.freqGHz,
            'refSynthFreq': self.refSynth.getFrequency(),
            'refSynthAmpl': self.refSynth.getAmplitude(),
            'refSynthOutput': self.refSynth.getRFOutput(),
            'outputPower': self.lastOutputPower
        }
    
    def autoRFPower(self, 
            powerDetect: PowerDetect_Interface, 
            targetSBPower: float,
            reinitialize: bool = False
        ) -> tuple[bool, str]:
        
        STEP_TIME = 0.1
        setpoint = targetSBPower

        if reinitialize or self.pid is None:
            self.setOutputPower(self.lastOutputPower)
            time.sleep(0.1)
            self.pid = PID(1, 0.1, 0.05, 
                setpoint = setpoint,
                sample_time = STEP_TIME,
                output_limits = (0, 100),
                starting_output = self.lastOutputPower
            )

        measured = powerDetect.read()
        success = False
        iter = 100
        while not success and iter > 0:
            control = self.pid(measured)
            self.setOutputPower(control)
            time.sleep(0.5)
            measured = powerDetect.read()
            if abs(measured - setpoint) < 0.5:
                success = True
            else:
                iter -= 1
            msg = f"SidebandSource.autoRFPower: iter:{iter} control:{control} %, powerLevel:{measured} dBm"
            print(msg, f"success:{success}")
        return success, msg