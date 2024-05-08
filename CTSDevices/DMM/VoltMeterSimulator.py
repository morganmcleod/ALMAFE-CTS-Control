import logging
from enum import Enum
from typing import List, Tuple, Optional
from .HP34401 import Function, TriggerSource, TriggerSlope, AutoZero, SampleSource
from random import randrange

class VoltMeterSimulator():

    def __init__(self):
        """Constructor

        """
        self.logger = logging.getLogger("ALMAFE-CTS-Control")

    def idQuery(self) -> bool:
        """Perform an ID query and check compatibility

        :return bool: True if the instrument is compatible with this class.
        """
        self.logger.info("VoltMeterSimulator.idQuery")
        return True
    
    def reset(self) -> bool:
        """Reset the instrument and set default configuration

        :return bool: True if write succeeded
        """
        self.logger.info("VoltMeterSimulator.reset")
        return True
    
    def isConnected(self) -> bool:
        return True
        
    def configureMeasurement(self, 
            function: Function, 
            autoRange: bool = True,
            manualResolution: float = 5.5, 
            manualRange: float = 1.0) -> None:
        self.funciton = Function
        self.autoRange = autoRange
        self.manualResolution = manualResolution
        self.manualRange = manualRange
    
    def configureAveraging(self, function: Function, nPowerLineCycles: float = 1):
        pass

    def configureAutoZero(self, autoZero: AutoZero = AutoZero.OFF):
        pass

    def readSinglePoint(self) -> Optional[float]:
        return randrange(0, 100) / 100

    def configureTrigger(self,
            triggerSource: TriggerSource,
            internalLevel: float = 0.0,
            slope: TriggerSlope = TriggerSlope.NEGATIVE,
            autoDelay: bool = True,
            manualDelay: float = 0.0) -> None:

        self.triggerSource = triggerSource
        self.internalLevel = internalLevel
        self.slope = slope
        self.autoDelay = autoDelay
        self.manualDelay = manualDelay


    def configureMultipoint(self,
            triggerCount: int = 1,
            sampleCount: int = 1,
            preTriggerSamples: int = 0,
            sampleInterval: float = 0.1,
            sampleSource: SampleSource = SampleSource.TRIGGER_DELAY) -> None:
        self.configuredMultipoint = True

    def initiateMeasurement(self) -> None:
        pass

    def fetchMeasurement(self, timeout: int = 10000) -> Tuple[bool, List[float]]:
        return True, [0]

