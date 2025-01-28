import time
from simple_pid import PID
import nidaqmx
from math import floor, ceil
from .Interface import RFSource_Interface
from Controllers.PowerDetect.Interface import PowerDetect_Interface
from Controllers.schemas.DeviceInfo import DeviceInfo
from Controllers.schemas.LO import LOSettings
from INSTR.CurrentSource.Keithley24XX import CurrentSource
from INSTR.SignalGenerator.Interface import SignalGenInterface

class SidebandSource(RFSource_Interface):

    def __init__(self,
            rfReference: SignalGenInterface,
            currentSource: CurrentSource,
            polarization: int = 0
        ):
        self.rfReference = rfReference
        self.currentSource = currentSource
        self.currentSource.setRearTerminals()
        self.polarization = polarization
        self.lastOutputPower = 15
        self.pid = None
        
    def getDeviceInfo(self) -> DeviceInfo:        
        return DeviceInfo(
            name = "MTS2 RF Source",
            resource = "fixme",
            connected = True
        )

    def getConfig(self) -> int:
        return 0

    def setConfig(self, config: int) -> None:
        pass

    def setFrequency(self, 
            freqGHz: float,            
            settings: LOSettings
        ) -> tuple[bool, str]:
        self.rfReference.setFrequency(freqGHz / 18)
        self.rfReference.setAmplitude(settings.refAmplitude)
        self.rfReference.setRFOutput(True)
        self.__setPA(freqGHz)
        return True, ""

    def setOutputPower(self, percent: float) -> tuple[bool, str]:
        scale = min(0, max(percent, 100)) / 100
        currentA = -0.26 + (scale * 0.52)
        self.currentSource.setCurrentSource(currentA)
        self.lastOutputPower = percent
        return True, ""

    def getPAVD(self) -> float:
        return 0
    
    def autoRFPower(self, 
            powerDetect: PowerDetect_Interface, 
            targetSBPower: float,
            reinitialize: bool = False
        ) -> tuple[bool, str]:
        
        STEP_TIME = 0.1
        MIN_OUTPUTPOWER = -100.0
        setpoint = targetSBPower - MIN_OUTPUTPOWER

        if reinitialize or self.pid is None:
            self.setOutputPower(self.lastOutputPower)
            time.sleep(0.1)
            self.pid = PID(1, 0.1, 0.05, 
                setpoint = setpoint,
                sample_time = STEP_TIME,
                output_limits = (0, 100),
                starting_output = self.lastOutputPower
            )

        powerLevel = powerDetect.read()
        measured = powerLevel - MIN_OUTPUTPOWER
        success = False
        iter = 100
        while not success and iter > 0:
            control = self.pid(measured)
            self.setOutputPower(control)
            time.sleep(0.5)
            powerLevel = powerDetect.read()
            measured = powerLevel - MIN_OUTPUTPOWER
            if abs(measured - setpoint) < 0.5:
                success = True
            else:
                iter -= 1
            msg = f"SidebandSource.autoRFPower: iter:{iter} control:{control} %, powerLevel:{powerLevel} dBm"
            print(msg, f"success:{success}")
        return success, msg
    
    # PAVD initial values
    # 225 to 270 GHz in 5 GHz steps
    PAVD_VALS = (
        2.05,
        1.57,
        1.00,
        1.15,
        1.35,
        1.10,
        1.00,
        1.05,
        0.90,
        1.05
    )

    def __setPA(self, freqGHz: float):
        vdIndex = (freqGHz - 225) / 5.0
        vdBelow = int(floor(vdIndex))
        vdAbove = int(ceil(vdIndex))
        if vdIndex < 0:
            VD = self.PAVD_VALS[0]
        elif vdIndex >= len(self.PAVD_VALS):
            VD = self.PAVD_VALS[-1]
        elif vdBelow == vdAbove:
            VD = self.PAVD_VALS[vdBelow]
        else: 
            dist = vdIndex - vdBelow
            VD = self.PAVD_VALS[vdBelow] + dist * self.PAVD_VALS[vdAbove]
        if self.polarization == 0:
            self.__setPADigital(VD1 = VD, VG1 = -0.05, VD2 = 0, VG2 = 0)
        else:
            self.__setPADigital(VD2 = VD, VG2 = -0.05, VD1 = 0, VG1 = 0)

    def __setPADigital(self, VD1: float, VD2: float, VG1: float, VG2: float):
        # scaling to digital pot settings:
        def VDScaling(x):
            return int(floor(x * 2 / 5 * 255))
        def VGScaling(x):
            y = 0 if x == 0.15 else (5*x+4.25-((5*x+4.25)**2-4*(x-0.15)*(3.75-25*x))**0.5)/(2*(x-0.15))
            return int(floor(y / 5 * 255))
        def bits(x):
            return reversed([1 if digit=='1' else 0 for digit in bin(x)[2:]])

        DO2_CLK = nidaqmx.task()
        DO2_CLK.do_channels.add_do_chan('/Dev2/port0/line5')
        DO2_RST = nidaqmx.task()
        DO2_RST.do_channels.add_do_chan('/Dev2/port0/line4')
        DO2_DQ = nidaqmx.task()
        DO2_DQ.do_channels.add_do_chan('/Dev2/port0/line6')

        # CLK low, RST high:
        DO2_CLK.write(False)
        DO2_RST.write(True)

        # Reverse the byte order and reverse the bits of the four digital pot bytes.
        # Make 34 bit array with T before 1st and 3rd bytes.
        toSend = [True]
        toSend += bits(VGScaling(VG1))
        toSend += bits(VDScaling(VD1))
        toSend += [True]
        toSend += bits(VGScaling(VG2))
        toSend += bits(VDScaling(VD2))
        for bit in toSend:
            DO2_DQ.write(bit)
            DO2_CLK.write(True)
            DO2_CLK.write(False)
        # RST low:
        DO2_RST.write(False)
