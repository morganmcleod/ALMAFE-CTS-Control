from .PNAInterface import *
from .BaseAgilentPNA import BaseAgilentPNA

class AgilentPNA(BaseAgilentPNA):

    def __init__(self, resource="GPIB0::13::INSTR", idQuery=True, reset=True):
        """Constructor

        :param str resource: VISA resource string, defaults to "GPIB0::13::INSTR"
        :param bool idQuery: If true, perform an ID query and check compatibility, defaults to True
        :param bool reset: If true, reset the instrument and set default configuration, defaults to True
        """
        super(AgilentPNA, self).__init__(resource, idQuery, reset)
    
    def setMeasConfig(self, config: MeasConfig):
        """Set the measurement configuration for a channel
        :param MeasConfig config
        """
        pass

    def setPowerConfig(self, config: PowerConfig):
        """Set the output power and attenuation configuration for a channel
        :param PowerConfig config
        """
        pass

    def getTrace(self) -> List[float]:
        """Get trace data as a list of float
        :return List[float]
        """
        pass

    
    def getAmpPhase(self) -> Tuple[List[float], List[float]]:
        """Get trace data as parallel lists of amplitude dB, phase deg
        :return Tuple[List[float], List[float]]
        """
        pass

