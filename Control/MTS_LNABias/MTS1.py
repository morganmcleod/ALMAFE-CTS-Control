from .Interface import LNABias_interface
from DBBand6Cart.schemas import PreampParam

class LNABias(LNABias_interface):
    """MTS1 LNA bias is not automated.  This is just a simulator that prints.
    """
    
    def __init__(self):
        self.configLNA1 = PreampParam()
        self.configLNA2 = PreampParam()

    def set_bias(self, 
            configLNA1: PreampParam,
            configLNA2: PreampParam
        ) -> tuple[bool, str]:
        
        print(f"LNABias.setBias:\nLNA1:{configLNA1}\nLNA2:{configLNA2}")
        return True, ""
    
    def set_enable(self, enable: bool) -> tuple[bool, str]:
        print(f"LNABias.setEnable:{enable}")
        return True, ""
    
    def read_bias(self) -> dict:
        return {
            'lna1': self.configLNA1.dict(),
            'lna2': self.configLNA2.dict(),
            'success': True
        }
