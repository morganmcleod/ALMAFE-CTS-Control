from .Interface import LNABias_Interface, SelectLNA
from DBBand6Cart.schemas import PreampParam

class LNABias(LNABias_Interface):
    """MTS1 LNA bias is not automated.  This is just a simulator that prints.
    """
    
    def __init__(self):
        self.configLNA1 = PreampParam()
        self.configLNA2 = PreampParam()

    def set_bias(self, 
            select: SelectLNA,
            config: PreampParam,
        ) -> tuple[bool, str]:
        
        print(f"LNABias.set_bias: {select} -> {config}")
        return True, ""
    
    def set_enable(self, 
            select: SelectLNA, 
            enable: bool
        ) -> tuple[bool, str]:
        print(f"LNABias.set_enable: {select} -> {enable}")
        return True, ""
    
    def read_bias(self, select: SelectLNA) -> dict:                
        return (self.configLNA1 if select == SelectLNA.LNA1 else self.configLNA2).model_dump()
