import time
from simple_pid import PID
from .Interface import LOControl_interface
from ..MTS_SISBias.Interface import SISBias_interface, SelectBias
from AMB.AMBConnectionItf import AMBConnectionItf
from AMB.LODevice import LODevice
from AMB.FEMCDevice import FEMCDevice
from INSTR.SignalGenerator.Keysight_PSG_MXG import SignalGenerator

class LOControl(LOControl_interface):

    def __init__(self,
            conn: AMBConnectionItf,
            nodeAddr: int = 0x13,
            femcPort: int = FEMCDevice.PORT_BAND6,
            polarization: int = 0,
            refSynthResource: str = "GPIB0::29::INSTR",
            ytoLowGHz: float = 12.22,
            ytoHighGHz: float = 14.77
        ):
        self.loDevice = LODevice(conn, nodeAddr, band = 6, femcPort = femcPort)
        self.refSynth = SignalGenerator(refSynthResource)
        self.setYTOLimits(ytoLowGHz, ytoHighGHz)
        self.polarization = polarization
        self.lastOutputPower = 15
        self.pid = None
        self.refSynthMinPower = -5
        self.refSynthMaxPower = 7
        self.coldMultiplier = LODevice.COLD_MULTIPLIERS[self.loDevice.band]
        self.warmMultiplier = LODevice.WARM_MULTIPLIERS[self.loDevice.band]

    def setYTOLimits(self, ytoLowGHz: float, ytoHighGHz: float) -> None:
        self.loDevice.setYTOLimits(ytoLowGHz, ytoHighGHz)

    def setFrequency(self, 
            freqGHz: float, 
            floogOffset: float = 0.01,      # GHz
            loopBWSelect: int = LODevice.LOOPBW_ALT,    # 15 MHz/V
            lockSBSelect: int = LODevice.LOCK_BELOW_REF
        ) -> tuple[bool, str]:
        if not self.refSynth.setFrequency((freqGHz / self.coldMultiplier + floogOffset) / self.warmMultiplier):
            return False, "LOControl.setFrequency: error setting synthesizer frequency"
        if not self.refSynth.setRFOutput(True):
            return False, "LOControl.setFrequency: error enabling synthesizer output"
        self.loDevice.selectLoopBW(loopBWSelect)
        self.loDevice.selectLockSideband(lockSBSelect)
        done = False
        error = False
        synthPower = self.refSynthMinPower        
        while not done and not error:
            self.refSynth.setAmplitude(synthPower)
            time.sleep(0.1)
            wcaFreq, _, _ = self.loDevice.lockPLL(freqGHz)
            if wcaFreq == 0:
                synthPower += 1
                if synthPower > self.refSynthMaxPower:
                    error = True
            else:
                done = True
                
        if error:
            wcaFreq, _, _ = self.loDevice.setLOFrequency(freqGHz)
            if wcaFreq == 0:
                return False, "LOControl.setFrequency: OUT OF RANGE"
            else:
                self.loDevice.setNullLoopIntegrator(True)
                return True, "LOControl.setFrequency: NO LOCK"
        else:
            return True, ""
        
    def setOutputPower(self, 
            percent: float,            
            paGateVolts: float = 0.05
        ) -> tuple[bool, str]:
        self.loDevice.setPABias(self.polarization, 2.5 * percent / 100, paGateVolts)
        self.lastOutputPower = percent

    def getMonitorData(self) -> dict:
        return {
            'YTO': self.loDevice.getYTO(),
            'PLL': self.loDevice.getPLL(),
            'AMC': self.loDevice.getAMC(),
            'PA': self.loDevice.getPA()
        }
    
    def autoLOPower(self, 
            sisBias: SISBias_interface, 
            targetMixerCurrent: float,
            reinitialize: bool = False
            ) -> tuple[bool, str]:
        
        STEP_TIME = 0.1

        if reinitialize or self.pid is None:
            self.setOutputPower(15)
            time.sleep(0.1)
            self.pid = PID(1, 0.1, 0.05, 
                setpoint = abs(targetMixerCurrent),
                sample_time = STEP_TIME,
                output_limits = (0, 100),
                starting_output = self.lastOutputPower
            )

        sis = sisBias.read_bias(SelectBias.SIS1)
        success = False
        iter = 100
        while not success and iter > 0:
            Ij = abs(sis['Ij']) * 1000
            control = self.pid(Ij)
            self.setOutputPower(control)
            time.sleep(STEP_TIME)
            sis = sisBias.read_bias(SelectBias.SIS1)
            if abs(Ij - abs(targetMixerCurrent)) <= 0.3:
                success = True
            else:
                iter -= 1
            msg = f"LOControl.autoLOPower: iter:{iter} control:{control} %, Ij:{Ij} uA"
        return success, msg