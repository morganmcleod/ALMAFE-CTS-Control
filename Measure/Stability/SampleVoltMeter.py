from .SampleInterface import SampleInterface
from CTSDevices.DMM.HP34401 import HP34401, Function, AutoZero
from AmpPhaseDataLib.Constants import Units, DataKind
from typing import Tuple, Optional


class SampleVoltMeter(SampleInterface):
    def __init__(self, voltMeter: HP34401):
        self.voltMeter = voltMeter

    def configure(self) -> None:
        self.voltMeter.configureMeasurement(Function.DC_VOLTAGE)
        self.voltMeter.configureAutoZero(AutoZero.OFF)
        self.voltMeter.configureAveraging(Function.DC_VOLTAGE, 1)

    def getSample(self) -> Tuple[float, Optional[float]]:
        return self.voltMeter.readSinglePoint(), None
    
    def getUnits(self) -> Tuple[Units, Optional[Units]]:
        return Units.VOLTS, None

    def getDataKind(self) -> DataKind:
        return DataKind.AMPLITUDE
