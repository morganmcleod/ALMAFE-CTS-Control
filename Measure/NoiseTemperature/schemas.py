from pydantic import BaseModel
from CTSDevices.PowerMeter.schemas import StdErrConfig

class WarmIFSettings(BaseModel):
    enable: bool = False
    attenStart: int = 0      # dB
    attenStop: int = 10
    attenStep: int = 1
    ifStart: float = 4.0     # GHz
    ifStop: float = 12.0
    ifStep: float = 0.1
    sensorAmbient: int = 7
    sensorIfHot: int = 1
    sensorIfCold: int = 3
    diodeVoltage: float = 28.0
    diodeCurrentLimit: float = 0.04
    diodeEnr: float = 15.4

class NoiseTempSettings(BaseModel):
    enable: bool = False
    loStart: float = 221.0
    loStop: float = 265.0
    loStep: float = 4.0
    ifStart: float = 4.0     # GHz
    ifStop: float = 12.0
    ifStep: float = 0.1
    sensorAmbient: int = 7
    targetPHot: float = -30.0
    chopperSpeed = 0.5       # rev/sec
    sampleRate = 50          # samples/sec
    powerMeterConfig: StdErrConfig = StdErrConfig(
        minS = 50,
        maxS = 600,
        stdErr = 500.0E-6,
        timeout = 0
    )

class ImageRejectSettings(BaseModel):
    enable: bool = False
    targetSidebandPower: float = 15.0   # dBm

class LoWGIntegritySettings(NoiseTempSettings):
    isLoWGIntegrity = True

class ImageRejectPowers(BaseModel):
    pol: int = 0
    PwrUSB_SrcUSB: float = 0
    PwrLSB_SrcUSB: float = 0
    PwrLSB_SrcLSB: float = 0
    PwrUSB_SrcLSB: float = 0

    def getText(self):
        return f"pol{self.pol}: {self.PwrUSB_SrcUSB}, {self.PwrLSB_SrcUSB}, {self.PwrLSB_SrcLSB}, {self.PwrUSB_SrcLSB}"

class NoiseTempPowers(BaseModel):
    pol: int = 0
    Phot_USB: float = 0
    Pcold_USB: float = 0
    Phot_USB_StdErr: float = 0
    Pcold_USB_StdErr: float = 0
    Phot_LSB: float = 0
    Pcold_LSB: float = 0
    Phot_LSB_StdErr: float = 0
    Pcold_LSB_StdErr: float = 0
    
    def getText(self):
        return f"pol{self.pol}: {self.Phot_USB}, {self.Pcold_USB}, {self.Phot_LSB}, {self.Pcold_LSB}\n" \
            +  f"errors: {self.Phot_USB_StdErr}, {self.Pcold_USB_StdErr}, {self.Phot_LSB_StdErr}, {self.Pcold_LSB_StdErr}"