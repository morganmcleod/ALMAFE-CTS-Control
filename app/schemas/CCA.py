from pydantic import BaseModel
from typing import Optional

class Tempsensors(BaseModel):
    '''
    The cold cartridge temperature sensors.
    
    0: 4K stage (bands 3-10).  1: 110K stage.  2: Pol0 mixer/LNA
    3: No connection/spare.    4: 15K stage.   5: Pol1 mixer/LNA
    '''
    temp0: float
    temp1: float
    temp2: float
    temp3: float
    temp4: float
    temp5: float
    def getText(self):
        return f"temp0:{self.temp0} temp1:{self.temp1} temp2:{self.temp2} temp3:{self.temp3} temp4:{self.temp4} temp5:{self.temp5}"

class SIS(BaseModel):
    '''
    SIS bias readings.
    
    Vj is mixer junction voltage.  Ij is junction current.
    Vmag is magnet voltage.  Imag is magnet current.
    averaging is the number of samples averaged for Ij and Imag.
    '''
    Vj: float
    Ij: float
    Vmag: float
    Imag: float
    averaging: int
    def getText(self):
        return f"Vj:{self.Vj} Ij:{self.Ij} Vmag:{self.Vmag} Imag:{self.Imag} averaging:{self.averaging}"
    
class SetSIS(BaseModel):
    '''
    SIS bias settings.
    
    pol is 0 or 1.  sis is 1 or 2.  These specifiy which mixer to bias.
    Vj is mixer junction voltage.   If None/null, no change.  
    Imag is magnet curent.  If None/null, no change.
    '''
    pol: int
    sis: int
    Vj: Optional[float] = None
    Imag: Optional[float] = None
    def getText(self):
        return f"pol:{self.pol} sis:{self.sis} Vj:{self.Vj} Imag:{self.Imag}"

class SetLNAEnable(BaseModel):
    '''
    LNA enable settings
    
    pol is 0 or 1.  If -1 enable both pols.
    lna is 1 or 2.  If -1 enable both LNAs.
    '''
    pol: Optional[int] = -1
    lna: Optional[int] = -1
    enable: bool
    def getText(self):
        polText = "pol" + "1 " if self.pol>=1 else ("both " if self.pol<=-1 else "0 ")
        lnaText = "lna" + "2 " if self.lna>=2 else ("both " if self.lna<=-1 else "1 ")
        return polText + lnaText + "enabled" if self.enable else "disabled"

class SetLNA(BaseModel):
    '''
    LNA bias settings

    pol is 0 or 1.  sis is 1 or 2.  These specifiy which LNA to bias.
    VD1..VD3 and ID1..ID3 are supported for all bands.
    VD4..VD6 and ID4..ID6 are only supported for bands 1 and 2.
    If any value is None/null, no change.
    '''
    pol: int
    lna: int
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
        ret += (f"VD1={self.VD1} " if self.VD1 is not None else "")
        ret += (f"VD2={self.VD2} " if self.VD2 is not None else "")
        ret += (f"VD3={self.VD3} " if self.VD3 is not None else "")
        ret += (f"VD4={self.VD4} " if self.VD4 is not None else "")
        ret += (f"VD5={self.VD5} " if self.VD5 is not None else "")
        ret += (f"VD6={self.VD6} " if self.VD6 is not None else "")
        ret += (f"ID1={self.ID1} " if self.ID1 is not None else "")
        ret += (f"ID2={self.ID2} " if self.ID2 is not None else "")
        ret += (f"ID3={self.ID3} " if self.ID3 is not None else "")
        ret += (f"ID4={self.ID4} " if self.ID4 is not None else "")
        ret += (f"ID5={self.ID5} " if self.ID5 is not None else "")
        ret += (f"ID6={self.ID6} " if self.ID6 is not None else "")
        return ret
    
class LNA(SetLNA):
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
        ret += (f"VG1={self.VG1} " if self.VG1 is not None else "")
        ret += (f"VG2={self.VG2} " if self.VG2 is not None else "")
        ret += (f"VG3={self.VG3} " if self.VG3 is not None else "")
        ret += (f"VG4={self.VG4} " if self.VG4 is not None else "")
        ret += (f"VG5={self.VG5} " if self.VG5 is not None else "")
        ret += (f"VG6={self.VG6} " if self.VG6 is not None else "")
        return ret

class SetLED(BaseModel):
    pol: int
    enable: bool
    def getText(self):
        return f"pol{self.pol} " + ("enabled" if self.enable else "disabled")
