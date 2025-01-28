import time
import logging
import threading
import yaml

from pydantic import BaseModel
from typing import List, Tuple
from bisect import bisect_left

from DebugOptions import *
from AMB.LODevice import LODevice
from AMB.CCADevice import CCADevice
from AMB.schemas.MixerTests import *
from app_Common.CTSDB import CTSDB
from DBBand6Cart.CartConfigs import CartConfigs
from DBBand6Cart.WCAs import WCAs, WCA
from DBBand6Cart.MixerParams import MixerParams, MixerParam
from DBBand6Cart.PreampParams import PreampParams, PreampParam
from ..PBAController import PBAController
from INSTR.SignalGenerator.Interface import SignalGenInterface
from .Interface import Receiver_Interface, AutoLOStatus, SelectSIS
from Controllers.schemas.LO import LOSettings

class CartAssemblySettings(BaseModel):
    serialNum: str = ""
    min_percent: int = 15
    max_percent: int = 100    
    max_iter: int = 15
    tolerance: float = 0.5   # uA
    sleep: float = 0.2
    freqLOGHz: float = 0
    loConfig: WCA = WCA()
    loSettings: LOSettings = LOSettings()

class CartAssembly(Receiver_Interface):
    CARTASSEMBLY_SETTINGS = "Settings/Settings_CartAssembly.yaml"

    def __init__(self, ccaDevice: CCADevice, loDevice: LODevice):
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.ccaDevice = ccaDevice
        self.loDevice = loDevice
        self.reset()
        self.loadSettings()
        self.controller = PBAController(
            tolerance = self.settings.tolerance,
            output_limits = (self.settings.min_percent, self.settings.max_percent),
            min_resolution = 0.0005,
            max_iter = self.settings.max_iter
        )
        
    def reset(self):
        self.configId = self.keysPol0 = self.keysPol1 = None
        self.mixerParam01 = None
        self.mixerParam02 = None
        self.mixerParam11 = None
        self.mixerParam12 = None
        self.mixerParams01 = None
        self.mixerParams02 = None
        self.mixerParams11 = None
        self.mixerParams12 = None
        self.preampParam01 = None
        self.preampParam02 = None
        self.preampParam11 = None
        self.preampParam12 = None
        self.preampParams01 = None
        self.preampParams02 = None
        self.preampParams11 = None
        self.preampParams12 = None        
        self.autoLOStatus = AutoLOStatus()

    def loadSettings(self):
        try:
            with open(self.CARTASSEMBLY_SETTINGS, "r") as f:
                d = yaml.safe_load(f)
                self.settings = CartAssemblySettings.model_validate(d)
                if self.settings.serialNum:
                    DB = CartConfigs(driver = CTSDB())
                    configs = DB.read(serialNum = self.settings.serialNum, latestOnly = True)
                    if configs:                    
                        self.setCartConfig(configs[0].key)
                    self.setLOConfig(self.settings.loConfig.key)
                    self.setBias(self.settings.freqLOGHz)
        except Exception as e:
            self.settings = CartAssemblySettings()
            self.saveSettings()
    
    def saveSettings(self):
        try:
            with open(self.CARTASSEMBLY_SETTINGS, "w") as f:
                yaml.dump(self.settings.model_dump(), f)
        except Exception as e:
            pass

    def setConfig(self, configId: int) -> bool:
        DB = CartConfigs(driver = CTSDB())
        self.reset()
        self.settings = CartAssemblySettings(loConfig = self.settings.loConfig)
        if configId == 0:
            self.saveSettings()
            return True, ""
        configs = DB.read(keyColdCart = configId)
        if not configs:
            return False, f"CartAssembly: configId {configId} not found."
        self.settings.serialNum = configs[0].serialNum
        self.saveSettings()
        
        self.keysPol0 = DB.readKeys(configId, pol = 0)
        self.keysPol1 = DB.readKeys(configId, pol = 1)
        if self.keysPol0 or self.keysPol1:
            self.configId = configId
        else:
            return False, f"CartAssembly: configId {configId} readKeys failed."

        DB = MixerParams(driver = CTSDB())
        if self.keysPol0:
            self.mixerParams01 = DB.read(self.keysPol0.keyChip1)
            self.mixerParams02 = DB.read(self.keysPol0.keyChip2)
        if self.keysPol1:
            self.mixerParams11 = DB.read(self.keysPol1.keyChip1)
            self.mixerParams12 = DB.read(self.keysPol1.keyChip2)
        DB = PreampParams(driver = CTSDB())
        if self.keysPol0:
            self.preampParams01 = DB.read(self.keysPol0.keyPreamp1)
            self.preampParams02 = DB.read(self.keysPol0.keyPreamp2)
        if self.keysPol1:
            self.preampParams11 = DB.read(self.keysPol1.keyPreamp1)
            self.preampParams12 = DB.read(self.keysPol1.keyPreamp2)
        return True, ""

    def getConfig(self) -> int:
        return self.configId if self.configId else 0
    
    def getPLL(self) -> dict:
        return self.loDevice.getPLL()

    def getPA(self) -> dict:
        return self.loDevice.getPA()

    def setLOConfig(self, configId:int) -> bool:
        DB = WCAs(driver = CTSDB())
        self.settingsLO = WCA()
        if configId == 0:
            self.saveSettings()
            return True
        configs = DB.read(configId)
        if not configs:
            return False
        self.settings.loConfig = configs[0]
        self.saveSettings()
        self.loDevice.setPABias(0, gateVoltage = self.settings.loConfig.VGp0)
        self.loDevice.setPABias(1, gateVoltage = self.settings.loConfig.VGp1)
        self.loDevice.setYTOLimits(self.settings.loConfig.ytoLowGHz, self.settings.loConfig.ytoHighGHz)

    def getLOConfig(self) -> WCA:
        return self.settings.loConfig

    def setBias(self, FreqLO:float, magnetOnly: bool = False) -> tuple[bool, str]:
        if not self.configId:
            return False, "CartAssembly.setBias: no configuration is selected."
        self.settings.freqLOGHz = FreqLO
        self.saveSettings()
        DB = MixerParams(driver = CTSDB())
        if self.mixerParams01:
            self.mixerParam01 = DB.interpolate(FreqLO, self.mixerParams01)
            self.ccaDevice.setSIS(0, 1, None if magnetOnly else self.mixerParam01.VJ, self.mixerParam01.IMAG)
        if self.mixerParams02:
            self.mixerParam02 = DB.interpolate(FreqLO, self.mixerParams02)
            self.ccaDevice.setSIS(0, 2, None if magnetOnly else self.mixerParam02.VJ, self.mixerParam02.IMAG)
        if self.mixerParams11:
            self.mixerParam11 = DB.interpolate(FreqLO, self.mixerParams11)
            self.ccaDevice.setSIS(1, 1, None if magnetOnly else self.mixerParam11.VJ, self.mixerParam11.IMAG)
        if self.mixerParams12:
            self.mixerParam12 = DB.interpolate(FreqLO, self.mixerParams12)
            self.ccaDevice.setSIS(1, 2, None if magnetOnly else self.mixerParam12.VJ, self.mixerParam12.IMAG)
        
        if not magnetOnly:
            if self.preampParams01:
                pp = self.preampParams01[0]
                self.ccaDevice.setLNA(0, 1, pp.VD1, pp.VD2, pp.VD3, 0, 0, 0,
                                            pp.ID1, pp.ID2, pp.ID3)
            if self.preampParams02:
                pp = self.preampParams02[0]
                self.ccaDevice.setLNA(0, 2, pp.VD1, pp.VD2, pp.VD3, 0, 0, 0,
                                        pp.ID1, pp.ID2, pp.ID3)
            if self.preampParams11:
                pp = self.preampParams11[0]
                self.ccaDevice.setLNA(1, 1, pp.VD1, pp.VD2, pp.VD3, 0, 0, 0,
                                            pp.ID1, pp.ID2, pp.ID3)
            if self.preampParams12:
                pp = self.preampParams12[0]
                self.ccaDevice.setLNA(1, 2, pp.VD1, pp.VD2, pp.VD3, 0, 0, 0,
                                            pp.ID1, pp.ID2, pp.ID3)                                    
            self.ccaDevice.setLNAEnable(True)
        return True, ""

    def readSISBias(self, select: SelectSIS, **kwargs) -> tuple[float, float]:
        averaging = kwargs.get('averaging', 1)
        pol = kwargs.get('pol', None)
        if pol is None:
            raise ValueError('paramter pol is required')
        return self.ccaDevice.getSIS(pol = pol, sis = select.value, averaging = averaging)        

    def autoLOPower(self, 
            reinitialize: bool = False, 
            **kwargs
        ) -> tuple[bool, str]:
        
        if not self.configId:
            return False, "CartAssembnly.autoLOPower: no configuration is selected."

        pol0 = kwargs.get('pol0', False)
        pol1 = kwargs.get('pol1', False)
    
        if not pol0 and not pol1:
            return False, "CartAssembly.autoLOPower: must enable at least one pol"
      
        if SIMULATE:
            return True, ""

        if kwargs.get('on_thread', False):
            threading.Thread(target = self._autoLOPowerSequence, args = (pol0, pol1), daemon = True).start()
            return True, ""
        else:
            return self._autoLOPowerSequence(pol0, pol1, reinitialize)

    def _autoLOPowerSequence(self, pol0: bool, pol1: bool, reinitialize: bool) -> tuple[bool, str]:
        success0 = success1 = True
        msg0 = msg1 = ""
        self.autoLOStatus.is_active = True        
        if pol0:
            self.autoLOStatus.polarization = 0
            success0, msg0 = self._autoLOPower(0, self.mixerParam01.IJ)
        if pol1:
            self.autoLOStatus.polarization = 1
            success1, msg1 = self._autoLOPower(1, self.mixerParam11.IJ)
        self.autoLOStatus.is_active = None
        return success0 & success1, msg0 + " " + msg1

    def _autoLOPower(self, pol, targetIJ = None) -> tuple[bool, str]:
        if targetIJ is None:
            try:
                targetIJ = abs(self.mixerParam01.IJ if pol == 0 else self.mixerParam11.IJ)
            except:
                return False, "CartAssembly._autoLOPower bias not available"
        
        self.logger.info(f"CartAssembly._autoLOPower: pol{pol} target Ij={targetIJ}")
        
        averaging = 2
        self.controller.reset()
        self.controller.setpoint = targetIJ
        paOutput = self.controller.output
        self.loDevice.setPAOutput(pol, paOutput)
        time.sleep(self.settings.sleep)
        sis = self.ccaDevice.getSIS(pol, sis = 1, averaging = averaging)
        if sis is None:
            return False, f"Error getting SIS bias readings for pol{pol}"

        sisCurrent = abs(sis['Ij'])

        done = error = False
        msg = ""

        while not done and not error:
            self.logger.info(f"CartAssembly.autoLOPower iter={self.controller.iter} PA={self.controller.output:.1f} % Ij={sisCurrent:.3f} uA")
            paOutput = self.controller.process(sisCurrent)
            if self.controller.done and not self.controller.fail:
                msg = f"CartAssembly.autoLOPower: success Ij={sisCurrent:.3f} uA"
                done = True
            elif self.controller.fail:
                msg = f"CartAssembly.autoLOPower: fail iter={self.controller.iter} max_iter={self.settings.max_iter} setValue={paOutput:.2f} %"
                error = True
            else:
                self.loDevice.setPAOutput(pol, paOutput)
                time.sleep(self.settings.sleep)
                sis = self.ccaDevice.getSIS(pol, sis = 1, averaging = averaging)
                sisCurrent = abs(sis['Ij'])

        if error:
            self.logger.error(msg)
            return error, msg
        elif msg:
            self.logger.info(msg)
            return True, ""
    
    def getAutoLOStatus(self) -> AutoLOStatus:
        return self.autoLOStatus

    def getTargetMixersBias(self, freqLO: float = None) -> tuple[MixerParam] | None:
        if not self.configId:
            self.logger.error("MixerAssembly.getTargetMixersBias: no configuration is selected.")
            return None
        if freqLO is not None:
            DB = MixerParams(driver = CTSDB())
            return (DB.interpolate(freqLO, self.mixerParams01), DB.interpolate(freqLO, self.mixerParams11))
        else:
            return (self.mixerParam01, self.mixerParam11)

    def setFrequency(self, 
            freqGHz:float, 
            settings: LOSettings
        ) -> tuple[bool, str]:
        self.loDevice.selectLockSideband(settings.lockSBSelect)
        wcaFreq, ytoFreq, ytoCourse = self.loDevice.setFrequency(freqGHz)
        pllConfig = self.loDevice.getPLLConfig()
        if self.loReference is not None:
            self.loReference.setFrequency((freqGHz / pllConfig['coldMult'] - settings.floogOffset) / pllConfig['warmMult'])
            self.loReference.setAmplitude(settings.refAmplitude)
            self.loReference.setRFOutput(True)
        if not SIMULATE:
            wcaFreq, ytoFreq, ytoCourse = self.loDevice.lockPLL()
        else:
            self.loDevice.setNullLoopIntegrator(True)
        return True, f"setFrequency: wca={wcaFreq}, yto={ytoFreq}, courseTune={ytoCourse}"

    def isLocked(self) -> bool:
        pll = self.loDevice.getLockInfo()
        return pll['isLocked']
