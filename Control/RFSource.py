from typing import Optional
import yaml
from app.database.CTSDB import CTSDB
from AMB.LODevice import LODevice
from AMB.AMBConnectionItf import AMBConnectionItf
from INSTR.SignalGenerator.Interface import SignalGenInterface
from DBBand6Cart.WCAs import WCAs, WCA
from DebugOptions import *

class RFSource(LODevice):

    FREQ_FLOOG = 0.020
    RFSRC_SETTINGS = "Settings/Settings_RFSource.yaml"

    def __init__(
            self, 
            conn: AMBConnectionItf, 
            nodeAddr: int, 
            band: int,                      # what band is the actual hardware
            femcPort:Optional[int] = None,  # optional override which port the band is connected to)
            paPol: int = 0                  # which polarization to operate for the RF source
        ):
        super().__init__(conn, nodeAddr, band, femcPort)
        self.loadSettings()
        self.paPol = paPol
        self.setPAOutput(self.paPol, 0)

    def loadSettings(self):
        try:
            with open(self.RFSRC_SETTINGS, "r") as f:
                d = yaml.safe_load(f)
                self.config = WCA.model_validate(d)
                if self.config.serialNum:
                    DB = WCAs(driver = CTSDB())
                    configs = DB.read(serialNum = self.config.serialNum)
                    if configs:
                        self.setRFSourceConfig(configs[0].key)
        
        except:
            self.config = WCA()
            self.saveSettings()

    def saveSettings(self):
        with open(self.RFSRC_SETTINGS, "w") as f:
            yaml.dump(self.config.dict(), f)

    def setRFSourceConfig(self, configId:int) -> bool:
        DB = WCAs(driver = CTSDB())
        self.config = WCA()
        if configId == 0:
            self.saveSettings()
            return True
        configs = DB.read(configId)
        if not configs:
            return False
        self.config = configs[0]
        self.saveSettings()
        self.setPABias(0, gateVoltage = self.config.VGp0)
        self.setPABias(1, gateVoltage = self.config.VGp1)

    def getRFSourceConfig(self) -> WCA:
        return self.config

    def connected(self) -> bool:
        return super().connected()
    
    def lockRF(self, rfReference: SignalGenInterface, freqRF: float, sigGenAmplitude: float = 10.0) -> tuple[bool, str]:
        self.selectLockSideband(self.LOCK_ABOVE_REF)
        wcaFreq, ytoFreq, ytoCourse = self.setLOFrequency(freqRF)
        if wcaFreq == 0:
            return False, "lockRF: frequency out of range"
        pllConfig = self.getPLLConfig()
        rfReference.setFrequency((freqRF / pllConfig['coldMult'] - self.FREQ_FLOOG) / pllConfig['warmMult'])
        rfReference.setAmplitude(sigGenAmplitude)
        rfReference.setRFOutput(True)
        if not SIMULATE:
            wcaFreq, ytoFreq, ytoCourse = self.lockPLL()
            success = wcaFreq != 0
        else:
            self.setNullLoopIntegrator(True)
            success = True
        return success, f"lockRF: wca={wcaFreq}, yto={ytoFreq}, courseTune={ytoCourse}"

    def getPAVD(self):
        pa = self.getPA()
        if self.paPol == 0:
            return pa['VDp0']
        elif self.paPol == 1:
            return pa['VDp1']

    def setPAOutput(self, pol: int, percent: float):
        self._paOutput = percent
        return super().setPAOutput(pol, percent)
    
    def getPAOutput(self) -> float:
        return self._paOutput
    
    def turnOff(self) -> None:
        self.setPAOutput(pol = self.paPol, percent = 0)
