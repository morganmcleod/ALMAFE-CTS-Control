from .Interface import LNABias_interface
from DBBand6Cart.schemas.PreampParam import PreampParam
from AMB.AMBConnectionItf import AMBConnectionItf
from AMB.CCADevice import CCADevice
from AMB.FEMCDevice import FEMCDevice

class LNABias(LNABias_interface):

    def __init__(self,
            conn: AMBConnectionItf,
            nodeAddr: int = 0x13,
            femcPort: int = FEMCDevice.PORT_BAND3,
            polarization: int = 1):
        
        self.ccaDevice = CCADevice(conn, nodeAddr, band = 6, port = femcPort)
        self.polarization = polarization

    def set_bias(self, 
            configLNA1: PreampParam,
            configLNA2: PreampParam
        ) -> tuple[bool, str]:
        
        success1 = self.ccaDevice.setLNA(
            self.polarization, 
            1, 
            configLNA1.VD1,
            configLNA1.VD2,
            configLNA1.VD3,
            None, None, None,
            configLNA1.ID1,
            configLNA1.ID2,
            configLNA1.ID3
        )
        success2 = self.ccaDevice.setLNA(
            self.polarization, 
            2, 
            configLNA2.VD1,
            configLNA2.VD2,
            configLNA2.VD3,
            None, None, None,
            configLNA2.ID1,
            configLNA2.ID2,
            configLNA2.ID3
        )
        if success1 and success2:
            return True, ""
        else:
            return False, f"LNABias.set_bias error LNA1:{success1}, LNA2:{success2}"
    
    def set_enable(self, enable: bool) -> tuple[bool, str]:
        success = self.ccaDevice.setLNAEnable(enable, self.polarization)
        return success, "" if success else "LNABias.set_enable error"
    
    def read_bias(self) -> dict:
        lna1 = self.ccaDevice.getLNA(self.polarization, 1)
        lna2 = self.ccaDevice.getLNA(self.polarization, 2)
        return {
            'lna1': lna1,
            'lna2': lna2,
            'success': True
        }
