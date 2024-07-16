from pydantic import BaseModel
from enum import Enum
from INSTR.PowerMeter.schemas import StdErrConfig
from INSTR.Chopper.Interface import ChopperState
from Control.IFSystem.Interface import InputSelect

class ChopperMode(Enum):
    SPIN = "SPIN"
    SWITCH = "SWITCH"

class BackEndMode(Enum):
    IF_PLATE = "IF_PLATE"
    SPEC_AN = "SPEC_AN"

class SelectPolarization(Enum):
    POL0 = "POL0"
    POL1 = "POL1"
    BOTH = "BOTH"

    def testPol(self, pol: int):        
        if self == SelectPolarization.BOTH:
            return True
        if self == SelectPolarization.POL0 and pol == 0:
            return True
        if self == SelectPolarization.POL1 and pol == 1:
            return True
        return False
    
class TestSteps(BaseModel):
    zeroPM: bool = True
    warmIF: bool = True
    noiseTemp: bool = True
    imageReject: bool = True
    loWGIntegrity: bool = False
    
    def getText(self):
        return f"zeroPM:{self.zeroPM} warmIF:{self.warmIF}, noiseTemp:{self.noiseTemp}, imageReject:{self.imageReject}, loWGIntegrity:{self.loWGIntegrity}"

class CommonSettings(BaseModel):
    backEndMode: str = BackEndMode.IF_PLATE.value
    targetPHot: float = -30.0
    imageRejectSBTarget_PM: float = -15.0   # dBm
    imageRejectSBTarget_SA: float = -30.0   # dBm
    chopperSpeed: float = 0.5               # rev/sec
    sampleRate: float = 50                  # samples/sec
    sensorAmbient: int = 7
    tColdEff: float = 80
    sigGenAmplitude: float = 10.0
    pauseForColdLoad: bool = True
    powerMeterConfig: StdErrConfig = StdErrConfig(
        minS = 50,
        maxS = 600,
        stdErr = 500.0E-6,
        timeout = 0
    )

class WarmIFSettings(BaseModel):
    attenStart: int = 5      # dB
    attenStop: int = 5
    attenStep: int = 1
    ifStart: float = 4.0     # GHz
    ifStop: float = 12.0
    ifStep: float = 0.1
    diodeVoltage: float = 28.0
    diodeCurrentLimit: float = 0.04
    diodeEnr: float = 15.4

class NoiseTempSettings(BaseModel):
    loStart: float = 221.0
    loStop: float = 265.0
    loStep: float = 4.0
    ifStart: float = 4.0     # GHz
    ifStop: float = 12.0
    ifStep: float = 0.1
    polarization: str = SelectPolarization.BOTH.value

class BiasOptSettings(BaseModel):
    vjMin: float = 4.0
    vjStep: float = 0.2
    vjMax: float = 5.0
    ijMin: float = 32.0
    ijStep: float = 2.0
    ijMax: float = 42.0
    polarization: str = SelectPolarization.BOTH.value

class YFactorSettings(BaseModel):
    inputSelect: InputSelect = InputSelect.POL0_USB
    ifStart: float = 5
    ifStop: float = 10

class ChopperPowers(BaseModel):
    inputName: str
    chopperState: ChopperState = ChopperState.TRANSITION
    power: float = 0

class SpecAnPowers(BaseModel):
    pol: int
    ifFreqs: list[float] = []
    pHotUSB: list[float] = []
    pColdUSB: list[float] = []
    pHotLSB: list[float] = []
    pColdLSB: list[float] = []

class YFactorSample(BaseModel):
    Y: float
    TRx: float
