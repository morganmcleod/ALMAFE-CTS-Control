from .SampleInterface import SampleInterface
from INSTR.PNA.PNAInterface import PNAInterface
from INSTR.PNA.AgilentPNA import DEFAULT_CONFIG, DEFAULT_POWER_CONFIG
from INSTR.PNA.schemas import TriggerSource
from AmpPhaseDataLib.Constants import Units, DataKind
from typing import Tuple, Optional
import copy

class SamplePNA(SampleInterface):
    def __init__(self, pna: PNAInterface):
        self.pna = pna

    def configure(self) -> None:
        self.pna.reset()
        try:
            self.pna.workaroundPhaseLockLost()
        except:
            pass
        self.pnaConfig = copy.copy(DEFAULT_CONFIG)        
        self.pnaConfig.triggerSource = TriggerSource.MANUAL
        self.pnaConfig.bandWidthHz = 35e3
        self.pna.setMeasConfig(self.pnaConfig)
        self.pna.setPowerConfig(DEFAULT_POWER_CONFIG)

    def getSample(self) -> Tuple[float, Optional[float]]:
        amp, phase = self.pna.getAmpPhase()
        return phase, amp

    def getUnits(self) -> Tuple[Units, Optional[Units]]:
        return Units.DEG, Units.DBM

    def getDataKind(self) -> DataKind:
        return DataKind.PHASE