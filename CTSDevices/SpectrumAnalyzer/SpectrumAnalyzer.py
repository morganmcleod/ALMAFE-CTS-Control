from .BaseMXA import BaseMXA

class SpectrumAnalyzer(BaseMXA):

    def __init__(self, resource="TCPIP0::10.1.1.7::inst0::INSTR", idQuery=True, reset=True) -> None:
        """Constructor

        :param str resource: VISA resource string, defaults to "GPIB0::13::INSTR"
        :param bool idQuery: If true, perform an ID query and check compatibility, defaults to True
        :param bool reset: If true, reset the instrument and set default configuration, defaults to True
        """
        super(SpectrumAnalyzer, self).__init__(resource, idQuery, reset)
   