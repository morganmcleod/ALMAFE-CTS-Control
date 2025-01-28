from typing import Optional
import yaml
from app_Common.CTSDB import CTSDB
from .Interface import RFSource_Interface
from AMB.LODevice import LODevice
from AMB.AMBConnectionItf import AMBConnectionItf
from Controllers.schemas.LO import LOSettings
from INSTR.SignalGenerator.Interface import SignalGenInterface
from DBBand6Cart.WCAs import WCAs, WCA
from DebugOptions import *

class RFSource(RFSource_Interface, LODevice):

    RFSRC_SETTINGS = "Settings/Settings_RFSource.yaml"

    def __init__(
            self,
            conn: AMBConnectionItf, 
            rfReference: SignalGenInterface,
            nodeAddr: int, 
            band: int,                      # what band is the actual hardware
            femcPort:Optional[int] = None,  # optional override which port the band is connected to)
            paPol: int = 0                  # which polarization to operate for the RF source
        ):
        LODevice.__init__(conn, nodeAddr, band, femcPort)
        self.rfReference = rfReference
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
                        self.setConfig(configs[0].key)
        
        except:
            self.config = WCA()
            self.saveSettings()

    def saveSettings(self):
        with open(self.RFSRC_SETTINGS, "w") as f:
            yaml.dump(self.config.dict(), f)

    def setConfig(self, configId:int) -> bool:
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

    def getConfig(self) -> int:
        return self.configId

    def connected(self) -> bool:
        return super().connected()
    
    def setFrequency(self, 
            freqGHz: float,            
            settings: LOSettings
        ) -> tuple[bool, str]:
        self.selectLockSideband(settings.lockSBSelect)
        wcaFreq, ytoFreq, ytoCourse = LODevice.setFrequency(self, freqGHz)
        if wcaFreq == 0:
            return False, "setFrequency: frequency out of range"
        if settings.setReference:
            pllConfig = LODevice.getPLLConfig(self)
            self.rfReference.setFrequency((freqGHz / pllConfig['coldMult'] - settings.floogOffset) / pllConfig['warmMult'])
            self.rfReference.setAmplitude(settings.refAmplitude)
            self.rfReference.setRFOutput(True)
        if not SIMULATE:
            wcaFreq, ytoFreq, ytoCourse = LODevice.lockPLL(self)
            success = wcaFreq != 0
        else:
            LODevice.setNullLoopIntegrator(self, True)
            success = True
        return success, f"e: wca={wcaFreq}, yto={ytoFreq}, courseTune={ytoCourse}"

    def getPAVD(self) -> float:
        pa = self.getPA()
        if self.paPol == 0:
            return pa['VDp0']
        elif self.paPol == 1:
            return pa['VDp1']

    def setPAOutput(self, pol: int, percent: float):
        self._paOutput = percent
        return LODevice.setPAOutput(self, pol, percent)
    
    def getPAOutput(self) -> float:
        return self._paOutput

