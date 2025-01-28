import typing
import time
from statistics import mean
from .Interface import SISMagnet_Interface
from Measure.Shared.SelectSIS import SelectSIS
from INSTR.PowerSupply.AgilentE363xA import PowerSupply
from INSTR.DMM.HP34401 import HP34401, Function

class SISMagnet(SISMagnet_Interface):

    def __init__(self,
            powerSupplyResource: str = "GPIB0::6::INSTR",
            dmmResource: str = "GPIB0::22::INSTR"
        ):
        self.powerSupply = PowerSupply(powerSupplyResource)
        self.powerSupply.setOutputEnable(False)
        self.dmm = HP34401(dmmResource)        
        self.dmm.configureMeasurement(Function.DC_CURRENT)
    
    def __del__(self):
        self.powerSupply.setOutputEnable(False)

    def setCurrent(self,
            currentMA: float,
            sisSelect: SelectSIS = SelectSIS.SIS1
        ) -> tuple[bool, str]:
        self.powerSupply.setCurrentLimit((currentMA + 0.1) / 1000)
        time.sleep(0.1)
        self.powerSupply.setVoltage(6)
        self.powerSupply.setOutputEnable(True)
    
    def readCurrent(self,
            averaging: int = 1,
            sisSelect: SelectSIS = SelectSIS.SIS1
        ) -> float:
        if averaging == 1:
            return self.dmm.readSinglePoint()
        else:
            self.dmm.configureMultipoint(1, averaging, 0, 0.005)
            self.dmm.initiateMeasurement()
            success, values = self.dmm.fetchMeasurement()
            if success:
                return mean(values)
            else:
                return -1.0
