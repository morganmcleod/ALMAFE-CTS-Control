from .Interface import LNABias_Interface, SelectLNA
from DBBand6Cart.schemas.PreampParam import PreampParam
from AMB.AMBConnectionItf import AMBConnectionItf
from AMB.CCADevice import CCADevice
from AMB.FEMCDevice import FEMCDevice

class LNABias(LNABias_Interface):

    def __init__(self,
            conn: AMBConnectionItf,
            nodeAddr: int = 0x13,
            femcPort: int = FEMCDevice.PORT_BAND3,
            polarization: int = 1):
        
        self.ccaDevice = CCADevice(conn, nodeAddr, band = 6, femcPort = femcPort)
        self.polarization = polarization

    def set_bias(self, 
            select: SelectLNA,
            config: PreampParam,
        ) -> tuple[bool, str]:
        success = self.ccaDevice.setLNA(
            self.polarization, 
            select.value, 
            config.VD1,
            config.VD2,
            config.VD3,
            None, None, None,
            config.ID1,
            config.ID2,
            config.ID3
        )
        if success:
            return True, ""
        else:
            return False, f"LNABias.set_bias error LNA1:{select}"
    
    def set_enable(self, 
            select: SelectLNA, 
            enable: bool
        ) -> tuple[bool, str]:
        success = self.ccaDevice.setLNAEnable(enable, self.polarization, select.value)
        return success, "" if success else "LNABias.set_enable error"
    
    def read_bias(self, select: SelectLNA) -> dict:
        return self.ccaDevice.getLNA(self.polarization, select.value)
