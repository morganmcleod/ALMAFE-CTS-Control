import typing
import time
from statistics import mean
from .Interface import SISMagnet_interface
from ..MTS_SISBias.Interface import SelectBias
from INSTR.CurrentSource.Keithley24XX import CurrentSource, CurrentRange, CurrentLevel

class SISMagnet(SISMagnet_interface):

    def __init__(self,
            currentSourceResource: str = "GPIB0::6::INSTR",
            dmmResource: str = "GPIB0::22::INSTR"
        ):
        self.currentSource = CurrentSource(currentSourceResource)
        self.currentSource.setRearTerminals()
        self.currentSource.setOutput(True)
    
    def __del__(self):
        self.currentSource.setOutput(False)

    def setCurrent(self,
            currentMA: float,
            sisSelect: SelectBias = SelectBias.SIS1
        ) -> tuple[bool, str]:
        self.currentSource.setCurrentSource(currentMA, 0.1, CurrentRange.BY_VALUE)
    
    def readCurrent(self,
            averaging: int = 1,
            sisSelect: SelectBias = SelectBias.SIS1
        ) -> float:
        return self.currentSource.readCurrent(averaging)
    