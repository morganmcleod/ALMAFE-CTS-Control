from typing import List, Optional
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
from simple_pid import PID

class CartAssembly():
    def __init__(self, ccaDevice: CCADevice, loDevice: LODevice, configId: Optional[int] = None):
        self.ccaDevice = ccaDevice
        self.loDevice = loDevice
        self.reset()
        if configId:
            self.setConfig(configId)
        
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
        self.ccaDevice.setSIS(0, 1, self.mixerParam01.VJ, self.mixerParam01.IMAG)
        self.ccaDevice.setSIS(0, 2, self.mixerParam02.VJ, self.mixerParam02.IMAG)
        self.ccaDevice.setSIS(1, 1, self.mixerParam01.VJ, self.mixerParam11.IMAG)
        self.ccaDevice.setSIS(1, 2, self.mixerParam02.VJ, self.mixerParam12.IMAG)
        return True

    def setAutoLOPower(self, pol: int) -> bool:
        if pol < 0 or pol > 1:
            raise ValueError("CartAssembly.setAutoLOPower: pol must be 0 or 1")

        targetIJ = abs(self.mixerParam01.IJ if pol == 0 else self.mixerParam11.IJ)
        print(f"target Ij = {targetIJ}")
        targetIJMin = targetIJ - 0.5   # uA
        targetIJMax = targetIJ + 0.5   # uA
        setVD = 1.0
        setVDMax = 2.5
        averaging = 2
        maxIter = 20

        self.loDevice.setPABias(pol, setVD)

        controller = PID(0.00675, 0.03, 0, setpoint = targetIJ, starting_output = setVD)
        controller.output_limits = (0, setVDMax)
        controller.sample_time = 0.1
        
        sis = self.ccaDevice.getSIS(pol, sis = 1, averaging = averaging)
        Ij = abs(sis['Ij']) * 1000
        if sis is None:
            raise ValueError("CartAssembly.setAutoLOPower: ccaDevice.getSIS() returned None")
        iter = maxIter
        while iter > 0 and not targetIJMin < abs(sis['Ij'] * 1000) < targetIJMax:
            print(maxIter - iter, round(setVD, 2), round(Ij, 3))
            setVD = controller(Ij)
            self.loDevice.setPABias(pol, setVD)
            sis = self.ccaDevice.getSIS(pol, sis = 1, averaging = averaging)
            Ij = abs(sis['Ij']) * 1000
            iter -= 1
        print(f"CartAssembly.setAutoLOPower: setVD={round(setVD, 2)} mV, IJ={round(Ij, 3)} uA, iter={iter}")
        return iter > 0

    def getSISCurrentTargets(self):
        return self.mixerParam01.IJ,  self.mixerParam02.IJ, self.mixerParam11.IJ,  self.mixerParam12.IJ

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