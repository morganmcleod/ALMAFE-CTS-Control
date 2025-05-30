from pydantic import BaseModel
from enum import Enum
from INSTR.PowerMeter.schemas import StdErrConfig
from INSTR.Chopper.Interface import ChopperState
from Controllers.IFSystem.Interface import InputSelect
from Controllers.PowerDetect.Interface import DetectMode
from Measure.Shared.SelectPolarization import SelectPolarization

class ChopperMode(Enum):
    SPIN = "SPIN"
    SWITCH = "SWITCH"

class BackEndMode(Enum):
    IF_PLATE = "IF_PLATE"
    SPEC_AN = "SPEC_AN"
    
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
    imageRejectSBTarget_SA: float = -40.0   # dBm
    chopperSpeed: float = 0.5               # rev/sec
    sampleRate: float = 20                  # samples/sec
    sensorAmbient: int = 6
    sensorMixer: int = 2
    tColdEff: float = 80
    loRefAmplitude: float = 5
    rfRefAmplitude: float = 15
    pauseForColdLoad: bool = True
    powerMeterConfig: StdErrConfig = StdErrConfig(
        minS = 50,
        maxS = 600,
        stdErr = 5.0E-4,
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
    ifOptimizeStart: float = 5.0
    ifOptimizeStop: float = 10.0
    vjStart: float = 7.5
    vjStop: float = 9.0
    vjStep: float = 0.5
    ijStart: float = 40.0
    ijStop: float = 60.0
    ijStep: float = 5.0
    iMag: float = 25.0
    outputDir: str = "testdata_local"

class BiasOptResult(BaseModel):
    freqLO: float
    VjSet: float
    IjSet: float
    IjRead: float
    Trx: float

class YFactorSettings(BaseModel):
    inputSelect: InputSelect = InputSelect.POL0_USB
    detectMode: DetectMode = DetectMode.DEFAULT
    ifStart: float = 5
    ifStop: float = 10
    attenuation: float = 20

class ChopperPowers(BaseModel):
    inputName: str
    chopperState: ChopperState = ChopperState.TRANSITION
    power: float = 0

class YFactorPowers(BaseModel):
    inputName: str
    pHot: float
    pCold: float

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
