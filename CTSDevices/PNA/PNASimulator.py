from .schemas import *
from .PNAInterface import *
from typing import Tuple, List, Optional
from random import gauss, random
from math import log10, pi, sqrt, atan2, exp

class PNASimulator(PNAInterface):

    def __init__(self, *args, **kwargs):
        pass
    
    def idQuery(self)-> Optional[str]:
        """Perform an ID query and check compatibility
        :return str: manufacturer and model or None
        """
        ret = "PNASimuilator"
        print("idQuery: " + ret)
        return ret
    
    def errorQuery(self) -> Tuple[int, str]:
        return (0, "")

    def reset(self) -> bool:
        """Reset instrument to defaults
        :return bool: True if reset successful
        """
        print("PNASimulator reset")
        return True
    
    def setMeasConfig(self, config: MeasConfig):
        """Set the measurement configuration for a channel
        :param MeasConfig config
        """
        self.measConfig = config
    
    def setPowerConfig(self, config: PowerConfig):
        """Set the output power and attenuation configuration for a channel
        :param PowerConfig config
        """
        self.powerConfig = config
    
    def getTrace(self, *args, **kwargs) -> List[float]:
        """Get trace data as a list of float        
        :return List[float]
        """
        # rescale x and y to -2..2.
        # exp(-(r^2)) = exp(-(sqrt(x^2 + y^2))^2) = exp(-(x^2 + y^2))
        y = kwargs.get('y', None)
        y = 2 * ((y - 150) / 75) if y else 0
        xSize = self.measConfig.sweepPoints
        return [exp(-((2 * (x - xSize) / xSize) ** 2 + y **2)) for x in range(xSize * 2)]
        
    def getAmpPhase(self) -> Tuple[float]:
        """Get instantaneous amplitude and phase
        :return (amplitude_dB, phase_deg)
        """
        real = gauss(0, 1)
        imag = gauss(0, 1)
        amp = 10 * log10(sqrt(real ** 2 + imag ** 2))
        phase = atan2(imag, real) * 180 / pi
        return (amp, phase)
