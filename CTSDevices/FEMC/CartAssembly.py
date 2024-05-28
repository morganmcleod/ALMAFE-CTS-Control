from typing import List, Optional, Tuple
from bisect import bisect_left
from AMB.LODevice import LODevice
from AMB.CCADevice import CCADevice

from app.database.CTSDB import CTSDB
from DBBand6Cart.CartConfigs import CartConfigs
from DBBand6Cart.schemas.CartConfig import CartKeys
from DBBand6Cart.MixerParams import MixerParams
from DBBand6Cart.PreampParams import PreampParams
from DBBand6Cart.schemas.MixerParam import MixerParam
from DBBand6Cart.schemas.PreampParam import PreampParam

from CTSDevices.Common.BinarySearchController import BinarySearchController
from CTSDevices.SignalGenerator.Interface import SignalGenInterface
import time
import logging
import threading
from DebugOptions import *

class CartAssembly():

    def __init__(self, ccaDevice: CCADevice, loDevice: LODevice, configId: Optional[int] = None):
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.ccaDevice = ccaDevice
        self.loDevice = loDevice
        self.reset()
        if configId:
            self.setConfig(configId)
        
    def reset(self):
        self.serialNum = None
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
        self.freqLOGHz = 0
        self.autoLOPol = None   # not used internally, but observed by CartAssembly API

    def setConfig(self, configId:int) -> bool:
        DB = CartConfigs(driver = CTSDB())
        self.reset()
        if configId == 0:
            return True
        configRecords = DB.read(keyColdCart = configId)
        if not configRecords:
            return False
        self.serialNum = configRecords[0].serialNum

        self.keysPol0 = DB.readKeys(configId, pol = 0)
        self.keysPol1 = DB.readKeys(configId, pol = 1)
        if self.keysPol0 or self.keysPol1:
            self.configId = configId
        else:
            return False
        DB = MixerParams(driver = CTSDB())
        if self.keysPol0:
            self.mixerParams01 = DB.read(self.keysPol0.keyChip1)
            self.mixerParams02 = DB.read(self.keysPol0.keyChip2)
        if self.keysPol1:
            self.mixerParams11 = DB.read(self.keysPol1.keyChip1)
            self.mixerParams12 = DB.read(self.keysPol1.keyChip2)
        DB = PreampParams(driver = CTSDB())
        if self.keysPol0:
            self.preampParams01: List[PreampParam] = DB.read(self.keysPol0.keyPreamp1)
            self.preampParams02: List[PreampParam] = DB.read(self.keysPol0.keyPreamp2)
        if self.keysPol1:
            self.preampParams11: List[PreampParam] = DB.read(self.keysPol1.keyPreamp1)
            self.preampParams12: List[PreampParam] = DB.read(self.keysPol1.keyPreamp2)
        return True

    def getConfig(self) -> int:
        return self.configId if self.configId else 0

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

    def setAutoLOPower(self, pol0: bool = True, pol1: bool = True, onThread: bool = False) -> tuple[bool, str]:
        if not pol0 and not pol1:
            return False, "setAutoLOPower: must enable at least one pol"

        if not self.configId:
            return False, "setAutoLOPower: no configId"
       
        if SIMULATE:
            return True, ""

        if onThread:
            threading.Thread(target = self.__autoLOPowerSequence, args = (pol0, pol1), daemon = True).start()
            return True, ""
        else:
            return self.__autoLOPowerSequence(pol0, pol1)

    def __autoLOPowerSequence(self, pol0: bool, pol1: bool) -> tuple[bool, str]:
        success0 = success1 = True
        msg0 = msg1 = ""
        if pol0:
            self.autoLOPol = 0
            success0, msg0 = self.__autoLOPower(0)
        if pol1:
            self.autoLOPol = 1
            success1, msg1 = self.__autoLOPower(1)
        return success0 & success1, msg0 + " " + msg1

    def __autoLOPower(self, pol) -> tuple[bool, str]:
        try:
            targetIJ = abs(self.mixerParam01.IJ if pol == 0 else self.mixerParam11.IJ)
        except:
            return False, f"No bias available for pol{pol}"
        
        self.logger.info(f"target Ij = {targetIJ}")
        paOutput = 20
        averaging = 2

        controller = BinarySearchController(
            outputRange = [0, 100], 
            initialStepPercent = 20, 
            initialOutput = paOutput, 
            setPoint = targetIJ,
            tolerance = 0.5,
            maxIter = 20)

        self.loDevice.setPAOutput(pol, paOutput)
        sis = self.ccaDevice.getSIS(pol, sis = 1, averaging = averaging)
        if sis is None:
            return False, f"Error getting SIS bias readings for pol{pol}"

        sisCurrent = abs(sis['Ij'])
        tprev = time.time()
        tsum = 0
        while not controller.isComplete():
            controller.process(sisCurrent)
            paOutput = controller.output
            self.loDevice.setPAOutput(pol, paOutput)
            time.sleep(0.1)
            sis = self.ccaDevice.getSIS(pol, sis = 1, averaging = averaging)
            sisCurrent = abs(sis['Ij'])
            self.logger.info(f"iter={controller.iter} PA={paOutput:.1f} % Ij={sisCurrent:.3f} uA")
            tsum += (time.time() - tprev)
            tprev = time.time()
        
        iterTime = tsum / (controller.iter + 1)
        msg = f"CartAssembly.__autoLOPower: pol{pol} PA={paOutput:.1f} %, IJ={sisCurrent:.3f} uA, iter={controller.iter} iterTime={round(iterTime, 2)} success={controller.success}"
        self.logger.info(msg)
        return controller.success, msg
    
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
            threading.Thread(target = self.__mixerDefluxSequence, args = (pol0, pol1, iMagMax, iMagStep), daemon = True).start()
            return True, ""
        else:
            return self.__mixerDefluxSequence(pol0, pol1, iMagMax, iMagStep)

    def __mixerDefluxSequence(self, 
            pol0: bool, 
            pol1: bool,
            iMagMax: float = 40.0, 
            iMagStep: float = 1.0) -> tuple[bool, str]:
    
        msg = f"mixersDeflux: "
        success0 = success1 = True
        if pol0:
            self.loDevice.setPABias(0, 0)
            success0 = self.ccaDevice.mixerDeflux(0, iMagMax, iMagStep)
            msg += f"pol0: {'success' if success0 else 'fail'}"
        if pol1:
            self.loDevice.setPABias(1, 0)
            success1 = self.ccaDevice.mixerDeflux(1, iMagMax, iMagStep)
            msg += f"pol1: {'success' if success1 else 'fail'}"

        return success0 & success1, msg