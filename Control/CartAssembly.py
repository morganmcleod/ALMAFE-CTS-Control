from pydantic import BaseModel
from typing import List, Tuple
from bisect import bisect_left
from AMB.LODevice import LODevice
from AMB.CCADevice import CCADevice

from app.database.CTSDB import CTSDB
from DBBand6Cart.CartConfigs import CartConfigs
from DBBand6Cart.MixerParams import MixerParams, MixerParam
from DBBand6Cart.PreampParams import PreampParams, PreampParam
from DBBand6Cart.WCAs import WCAs, WCA

from Control.PBAController import PBAController
from INSTR.SignalGenerator.Interface import SignalGenInterface
import time
import logging
import threading
from DebugOptions import *
import yaml

class CartAssemblySettings(BaseModel):
    serialNum: str = ""
    min_percent: int = 15
    max_percent: int = 100    
    max_iter: int = 15
    tolerance: float = 0.5   # uA
    sleep: float = 0.2

class IVCurveResult(BaseModel):
    VjSet: list[float] = []
    VjRead: list[float] = []
    IjRead: list[float] = []

    def is_valid(self) -> bool:
        return self.VjSet and self.VjRead and self.IjRead
    
    def assign(self, VjSet, VjRead, IjRead) -> None:
        self.VjSet = VjSet
        self.VjRead = VjRead
        self.IjRead = IjRead

class IVCurveResults(BaseModel):
    curve01: IVCurveResult = IVCurveResult()
    curve02: IVCurveResult = IVCurveResult()
    curve11: IVCurveResult = IVCurveResult()
    curve12: IVCurveResult = IVCurveResult()

class CartAssembly():

    CARTASSEMBLY_SETTINGS = "Settings_CartAssembly.yaml"
    LO_SETTINGS = "Settings_LO.yaml"

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
        self.ivCurveResults = IVCurveResults()
        self.freqLOGHz = 0
        self.autoLOPol = None   # not used internally, but observed by CartAssembly API        

    def loadSettings(self):
        try:
            with open(self.CARTASSEMBLY_SETTINGS, "r") as f:
                d = yaml.safe_load(f)
                self.settings = CartAssemblySettings.model_validate(d)
                if self.settings.serialNum:
                    DB = CartConfigs(driver = CTSDB())
                    configs = DB.read(serialNum = self.settings.serialNum, latestOnly = True)
                    if configs:                    
                        self.setConfig(configs[0].id)
        except:
            self.settings = CartAssemblySettings()
        try:
            with open(self.LO_SETTINGS, "r") as f:
                d = yaml.safe_load(f)
                self.wca = WCA.model_validate(d)
                if self.wca.serialNum:
                    DB = WCAs(driver = CTSDB())
                    configs = DB.read(serialNum = self.wca.serialNum)
                    if configs:
                        self.setLOConfig(configs[0].id)
        except:
            self.wca = WCA()
        self.saveSettings()

    def saveSettings(self):
        if not self.configId:
            self.settings.serialNum = ""
        with open(self.CARTASSEMBLY_SETTINGS, "w") as f:
            yaml.dump(self.settings.dict(), f)
        with open(self.LO_SETTINGS, "w") as f:
            yaml.dump(self.wca.dict(), f)

    def setConfig(self, configId:int) -> bool:
        DB = CartConfigs(driver = CTSDB())
        self.reset()
        if configId == 0:
            return True
        configs = DB.read(keyColdCart = configId)
        if not configs:
            return False
        self.settings.serialNum = configs[0].serialNum
        
        self.keysPol0 = DB.readKeys(configId, pol = 0)
        self.keysPol1 = DB.readKeys(configId, pol = 1)
        if self.keysPol0 or self.keysPol1:
            self.configId = configId
        else:
            return False
        
        self.saveSettings()

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
        return True

    def getConfig(self) -> int:
        return self.configId if self.configId else 0
    
    def setLOConfig(self, configId:int) -> bool:
        DB = WCAs(driver = CTSDB())
        self.wca = WCA()
        if configId == 0:
            return True
        configs = DB.read(configId)
        if not configs:
            return False
        self.wca = configs[0]
        self.saveSettings()

    def getLOConfig(self) -> WCA:
        return self.wca

    def setRecevierBias(self, FreqLO:float) -> bool:
        if not self.configId:
            return False
        if self.mixerParams01:
            self.mixerParam01 = self.__interpolateMixerParams(FreqLO, self.mixerParams01)
            self.ccaDevice.setSIS(0, 1, self.mixerParam01.VJ, self.mixerParam01.IMAG)
        if self.mixerParams02:
            self.mixerParam02 = self.__interpolateMixerParams(FreqLO, self.mixerParams02)
            self.ccaDevice.setSIS(0, 2, self.mixerParam02.VJ, self.mixerParam02.IMAG)
        if self.mixerParams11:
            self.mixerParam11 = self.__interpolateMixerParams(FreqLO, self.mixerParams11)
            self.ccaDevice.setSIS(1, 1, self.mixerParam11.VJ, self.mixerParam11.IMAG)
        if self.mixerParams12:
            self.mixerParam12 = self.__interpolateMixerParams(FreqLO, self.mixerParams12)
            self.ccaDevice.setSIS(1, 2, self.mixerParam12.VJ, self.mixerParam12.IMAG)
        
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
        return True

    def autoLOPower(self, pol0: bool = True, pol1: bool = True, onThread: bool = False, targetIJ = None) -> tuple[bool, str]:
        if not pol0 and not pol1:
            return False, "autoLOPower: must enable at least one pol"

        if not self.configId:
            return False, "autoLOPower: no configId"
       
        if SIMULATE:
            return True, ""

        if onThread:
            threading.Thread(target = self.__autoLOPowerSequence, args = (pol0, pol1, targetIJ), daemon = True).start()
            return True, ""
        else:
            return self.__autoLOPowerSequence(pol0, pol1)

    def __autoLOPowerSequence(self, pol0: bool, pol1: bool, targetIJ = None) -> tuple[bool, str]:
        success0 = success1 = True
        msg0 = msg1 = ""
        if pol0:
            self.autoLOPol = 0
            success0, msg0 = self.__autoLOPower(0, targetIJ)
        if pol1:
            self.autoLOPol = 1
            success1, msg1 = self.__autoLOPower(1, targetIJ)
        self.autoLOPol = None
        return success0 & success1, msg0 + " " + msg1

    def __autoLOPower(self, pol, targetIJ = None) -> tuple[bool, str]:
        if targetIJ is None:
            try:
                targetIJ = abs(self.mixerParam01.IJ if pol == 0 else self.mixerParam11.IJ)
            except:
                return False, f"No bias available for pol{pol}"
        
        self.logger.info(f"target Ij = {targetIJ}")
        
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
    
    def getSISCurrentTargets(self) -> Tuple[float, float, float, float]:
        return (self.mixerParam01.IJ, self.mixerParam02.IJ, self.mixerParam11.IJ,  self.mixerParam12.IJ)

    def __interpolateMixerParams(self, FreqLO:float, mixerParams:List[MixerParam]) -> MixerParam:
        # workaround for Python 3.9
        # 3.10 allows us to pass a key function to bisect_left
        FreqLOs = [x.FreqLO for x in mixerParams]
        
        pos = bisect_left(FreqLOs, FreqLO)
        if pos == 0:
            return mixerParams[0]
        if pos == len(mixerParams):
            return mixerParams[-1]
        if mixerParams[pos].FreqLO == FreqLO:
            return mixerParams[pos]
        before = mixerParams[pos - 1]
        after = mixerParams[pos]
        scale = (FreqLO - before.FreqLO) / (after.FreqLO - before.FreqLO)
        return MixerParam(
            FreqLO = FreqLO,
            VJ = before.VJ + ((after.VJ - before.VJ) * scale),
            IJ = before.IJ + ((after.IJ - before.IJ) * scale),
            IMAG = before.IMAG + ((after.IMAG - before.IMAG) * scale)
        )

    def lockLO(self, loReference: SignalGenInterface, freqLO: float) -> Tuple[bool, str]:
        self.loDevice.selectLockSideband(self.loDevice.LOCK_ABOVE_REF)
        wcaFreq, ytoFreq, ytoCourse = self.loDevice.setLOFrequency(freqLO)
        pllConfig = self.loDevice.getPLLConfig()
        loReference.setFrequency((freqLO / pllConfig['coldMult'] - 0.020) / pllConfig['warmMult'])
        loReference.setAmplitude(12.0)
        loReference.setRFOutput(True)
        if not SIMULATE:
            wcaFreq, ytoFreq, ytoCourse = self.loDevice.lockPLL()
        else:
            self.loDevice.setNullLoopIntegrator(True)
        return True, f"lockLO: wca={wcaFreq}, yto={ytoFreq}, courseTune={ytoCourse}"

    def isLocked(self) -> bool:
        pll = self.loDevice.getLockInfo()
        return pll['isLocked']

    def mixersDeflux(self, 
            pol0: bool = True, 
            pol1: bool = True, 
            iMagMax: float = 40.0, 
            iMagStep: float = 1.0, 
            onThread: bool = False) -> tuple[bool, str]:
        
        if not pol0 and not pol1:
            return False, "mixersDeflux: must enable at least one pol"
       
        if SIMULATE:
            return True, ""

        if onThread:
            threading.Thread(target = self._mixerDefluxSequence, args = (pol0, pol1, iMagMax, iMagStep), daemon = True).start()
            return True, ""
        else:
            return self._mixerDefluxSequence(pol0, pol1, iMagMax, iMagStep)

    def _mixerDefluxSequence(self, 
            pol0: bool, 
            pol1: bool,
            iMagMax: float = 40.0, 
            iMagStep: float = 1.0) -> tuple[bool, str]:
    
        msg = f"mixersDeflux: "
        success0 = success1 = True
        if pol0:
            self.loDevice.setPABias(0, 0)
            success0 = self.ccaDevice.mixerDeflux(0, iMagMax, iMagStep)
            msg += f"pol0: {'success' if success0 else 'fail'} "
        if pol1:
            self.loDevice.setPABias(1, 0)
            success1 = self.ccaDevice.mixerDeflux(1, iMagMax, iMagStep)
            msg += f"pol1: {'success' if success1 else 'fail'} "

        return success0 and success1, msg
    
    def IVCurve(self,
            pol0: bool = True,
            pol1: bool = True, 
            sis1: bool = True,
            sis2: bool = True,
            vjStart: float = None,
            vjStop: float = None,
            vjStep: float = None,
            onThread: bool = False
        ) -> tuple[bool, str]:

        if not pol0 and not pol1:
            return False, "IVCurve: must enable at least one pol"
    
        if not sis1 and not sis2:
            return False, "IVCurve: must enable at least one SIS"
       
        if onThread:
            threading.Thread(target = self._mixerDefluxSequence, args = (pol0, pol1, sis1, sis2, vjStart, vjStop, vjStep), daemon = True).start()
            return True, ""
        else:
            return self._IVCurveSequence(pol0, pol1, sis1, sis2, vjStart, vjStop, vjStep)
        
    def _IVCurveSequence(self,
            pol0: bool = True,
            pol1: bool = True, 
            sis1: bool = True,
            sis2: bool = True,
            vjStart: float = None,
            vjStop: float = None,
            vjStep: float = None
        ) -> tuple[bool, str]:
        self.ivCurveResults = IVCurveResults()
        msg = "I-V Curve: "
        if pol0:
            if sis1:
                VjSet, VjRead, IjRead = self.ccaDevice.IVCurve(0, 1, vjStart, vjStop, vjStep)
                self.ivCurveResults.curve01.assign(VjSet, VjRead, IjRead)
                msg += f"pol0 sis1: {'success' if self.ivCurveResults.curve01.is_valid else 'fail'} "
            if sis2:
                VjSet, VjRead, IjRead = self.ccaDevice.IVCurve(0, 2, vjStart, vjStop, vjStep)
                self.ivCurveResults.curve02.assign(VjSet, VjRead, IjRead)
                msg += f"pol0 sis2: {'success' if self.ivCurveResults.curve02.is_valid else 'fail'} "
        if pol1:
            if sis1:
                VjSet, VjRead, IjRead = self.ccaDevice.IVCurve(1, 1, vjStart, vjStop, vjStep)
                self.ivCurveResults.curve11.assign(VjSet, VjRead, IjRead)
                msg += f"pol1 sis1: {'success' if self.ivCurveResults.curve11.is_valid else 'fail'} "
            if sis2:
                VjSet, VjRead, IjRead = self.ccaDevice.IVCurve(1, 2, vjStart, vjStop, vjStep)
                self.ivCurveResults.curve12.assign(VjSet, VjRead, IjRead)
                msg += f"pol1 sis2: {'success' if self.ivCurveResults.curve12.is_valid else 'fail'} "
        return True, msg