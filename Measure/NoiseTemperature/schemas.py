from pydantic import BaseModel
from CTSDevices.PowerMeter.schemas import StdErrConfig
from CTSDevices.Chopper.Band6Chopper import State

class TestSteps(BaseModel):
    warmIF: bool = True
    noiseTemp: bool = True
    imageReject: bool = True
    loWGIntegrity: bool = False
    
    def getText(self):
        return f"warmIF:{self.warmIF}, noiseTemp:{self.noiseTemp}, imageReject:{self.imageReject}, loWGIntegrity:{self.loWGIntegrity}"

class CommonSettings(BaseModel):
    targetPHot: float = -30.0
    targetSidebandPower: float = -15.0  # dBm for image reject only
    chopperSpeed: float = 0.5           # rev/sec
    sampleRate: float = 50              # samples/sec
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
    
class ChopperPowers(BaseModel):
    input: str
    chopperState: State = State.TRANSITION
    power: float = 0

class YFactorSample(BaseModel):
    Y: float
    TRx: float
