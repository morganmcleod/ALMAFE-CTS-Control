from typing import List
from bisect import bisect_right
from AMB.LODevice import LODevice
from AMB.CCADevice import CCADevice

from ..database.CTSDB import CTSDB

from DBBand6Cart.CartConfigs import CartConfigs
from DBBand6Cart.schemas.CartConfig import CartKeys
from DBBand6Cart.MixerParams import MixerParams
from DBBand6Cart.PreampParams import PreampParams
from DBBand6Cart.schemas.MixerParam import MixerParam
from DBBand6Cart.schemas.PreampParam import PreampParam

class CartAssembly():
    def __init__(self, ccaDevice:CCADevice, loDevice:LODevice):
        self.ccaDevice = ccaDevice
        self.loDevice = loDevice
        self.reset()
        
    def reset(self):
        self.configId = self.keysPol0 = self.keysPol1 = None
        self.freqLOGHz = 0

    def setConfig(self, configId:int) -> bool:
        DB = CartConfigs(driver = CTSDB())
        keysPol0 = DB.readKeys(configId, pol = 0)
        keysPol1 = DB.readKeys(configId, pol = 1)
        if keysPol0 and keysPol1:
            self.configId = configId
        else:
            return False
        DB = MixerParams(driver = CTSDB())
        self.mixerParams01 = DB.read(keysPol0.keyChip1)
        self.mixerParams02 = DB.read(keysPol0.keyChip2)
        self.mixerParams11 = DB.read(keysPol1.keyChip1)
        self.mixerParams12 = DB.read(keysPol1.keyChip2)
        DB = PreampParams(driver = CTSDB())
        self.preampParams01 = DB.read(keysPol0.keyPreamp1)
        self.preampParams02 = DB.read(keysPol0.keyPreamp2)
        self.preampParams11 = DB.read(keysPol1.keyPreamp1)
        self.preampParams12 = DB.read(keysPol1.keyPreamp2)
        return True

    def setRecevierBias(self, FreqLO:float) -> bool:
        if not self.configId:
            return False
        self.mixerParam01 = self.__interpolateMixerParams(FreqLO, self.mixerParams01)
        self.mixerParam02 = self.__interpolateMixerParams(FreqLO, self.mixerParams02)
        self.mixerParam11 = self.__interpolateMixerParams(FreqLO, self.mixerParams11)
        self.mixerParam12 = self.__interpolateMixerParams(FreqLO, self.mixerParams12)
        self.ccaDevice.setSIS(0, 1, self.mixerParam01.VJ, self.mixerParam01.Imag)
        self.ccaDevice.setSIS(0, 2, self.mixerParam02.VJ, self.mixerParam02.Imag)
        self.ccaDevice.setSIS(1, 1, self.mixerParam01.VJ, self.mixerParam11.Imag)
        self.ccaDevice.setSIS(1, 2, self.mixerParam02.VJ, self.mixerParam12.Imag)

    def getSISCurrentTargets(self):
        return self.mixerParam01.IJ,  self.mixerParam02.IJ, self.mixerParam11.IJ,  self.mixerParam12.IJ

    def __interpolateMixerParams(self, FreqLO:float, mixerParams:List[MixerParam]) -> MixerParam:
        pos = bisect_right(mixerParams, FreqLO, key=lambda x:x.FreqLO)
        if pos == 0:
            return mixerParams[0]
        if pos == len(mixerParams):
            return mixerParams[-1]
        if mixerParams[pos].FreqLO == FreqLO:
            return mixerParams[pos]
        before = mixerParams[pos]
        after = mixerParams[pos + 1]
        scale = FreqLO / (after.FreqLO - before.FreqLO)
        return MixerParam(
            FreqLO = FreqLO    
            VJ = before.VJ + ((after.VJ - before.VJ) * scale)
            IJ = before.IJ + ((after.IJ - before.IJ) * scale)
            IMAG = before.IMAG + ((after.IMAG - before.IMAG) * scale)
        )