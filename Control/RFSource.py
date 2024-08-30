from AMB.LODevice import LODevice
from AMB.AMBConnectionItf import AMBConnectionItf
from INSTR.SignalGenerator.Interface import SignalGenInterface

from typing import Optional
from DebugOptions import *

class RFSource(LODevice):

    FREQ_FLOOG = 0.020

    def __init__(
            self, 
            conn: AMBConnectionItf, 
            nodeAddr: int, 
            band: int,                      # what band is the actual hardware
            femcPort:Optional[int] = None,  # optional override which port the band is connected to)
            paPol: int = 0                  # which polarization to operate for the RF source
        ):
        super().__init__(conn, nodeAddr, band, femcPort)
        self.paPol = paPol
        self.setPAOutput(self.paPol, 0)

    def connected(self) -> bool:
        return super().connected()
    
    def lockRF(self, rfReference: SignalGenInterface, freqRF: float, sigGenAmplitude: float = 10.0) -> tuple[bool, str]:
        self.selectLockSideband(self.LOCK_ABOVE_REF)
        wcaFreq, ytoFreq, ytoCourse = self.setLOFrequency(freqRF)
        if wcaFreq == 0:
            return False, "lockRF: frequency out of range"
        pllConfig = self.getPLLConfig()
        rfReference.setFrequency((freqRF / pllConfig['coldMult'] - self.yarFREQ_FLOOG) / pllConfig['warmMult'])
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
    