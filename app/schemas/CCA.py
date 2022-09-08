from pydantic import BaseModel
from typing import Optional

class Tempsensors(BaseModel):
    temp0: float
    temp1: float
    temp2: float
    temp3: float
    temp4: float
    temp5: float

class SIS(BaseModel):
    Vj: float
    Ij: float
    Vmag: float
    Imag: float
    averaging: int

class LNABias(BaseModel):
    '''
    For setting LNA bias
    '''
    VD1: Optional[float] = None
    VD2: Optional[float] = None
    VD3: Optional[float] = None
    VD4: Optional[float] = None
    VD5: Optional[float] = None
    VD6: Optional[float] = None
    ID1: Optional[float] = None
    ID2: Optional[float] = None
    ID3: Optional[float] = None
    ID4: Optional[float] = None
    ID5: Optional[float] = None
    ID6: Optional[float] = None
    def getText(self):
        ret = ""
        ret += (f"VD1={self.VD1} " if self.VD1 else "")
        ret += (f"VD2={self.VD2} " if self.VD2 else "")
        ret += (f"VD3={self.VD3} " if self.VD3 else "")
        ret += (f"VD4={self.VD4} " if self.VD4 else "")
        ret += (f"VD5={self.VD5} " if self.VD5 else "")
        ret += (f"VD6={self.VD6} " if self.VD6 else "")
        ret += (f"ID1={self.ID1} " if self.ID1 else "")
        ret += (f"ID2={self.ID2} " if self.ID2 else "")
        ret += (f"ID3={self.ID3} " if self.ID3 else "")
        ret += (f"ID4={self.ID4} " if self.ID4 else "")
        ret += (f"ID5={self.ID5} " if self.ID5 else "")
        ret += (f"ID6={self.ID6} " if self.ID6 else "")
        return ret
    
class LNA(LNABias):
    '''
    For reading all LNA bias monitor data
    '''
    enable: bool
    VG1: float
    VG2: float
    VG3: float
    VG4: Optional[float] = None
    VG5: Optional[float] = None
    VG6: Optional[float] = None
    def getText(self):
        biasText = super(LNA, self).getText() 
        ret = "enabled" if self.enable else "disabled" + biasText
        ret += (f"VG1={self.VG1} " if self.VG1 else "")
        ret += (f"VG2={self.VG2} " if self.VG2 else "")
        ret += (f"VG3={self.VG3} " if self.VG3 else "")
        ret += (f"VG4={self.VG4} " if self.VG4 else "")
        ret += (f"VG5={self.VG5} " if self.VG5 else "")
        ret += (f"VG6={self.VG6} " if self.VG6 else "")
        return ret
        

class SISOpenLoop(BaseModel):
    enable: bool

class Heater(BaseModel):
    current: float
