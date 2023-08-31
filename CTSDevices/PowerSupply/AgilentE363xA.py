from CTSDevices.Common.RemoveDelims import removeDelims   #todo move Common out of CTSDevices
import pyvisa
import re
import logging

class PowerSupply():
    """The Agilent E363xA power supply"""
    
    DEFAULT_TIMEOUT = 15000     # milliseconds
    
    def __init__(self, resource="GPIB0::5::INSTR", idQuery=True, reset=True):
        """Constructor

        :param str resource: VISA resource string
        :param bool idQuery: If true, perform an ID query and check compatibility, defaults to True
        :param bool reset: If true, reset the instrument and set default configuration, defaults to True
        """
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        rm = pyvisa.ResourceManager()
        self.inst = rm.open_resource(resource)
        self.inst.timeout = self.DEFAULT_TIMEOUT
        self.mfr = None
        self.model = None        

        ok = True
        if ok and idQuery:
            ok = self.idQuery()
        if ok and reset:
            ok = self.reset()

    def __del__(self):
        """Destructor
        """
        self.inst.close()
    
    def idQuery(self) -> bool:
        """Perform an ID query and check compatibility

        :return bool: True if the instrument is compatible with this class.
        """
        self.mfr = None
        self.model = None
        response = self.inst.query("*IDN?")
        match = re.match(r"[ ]*((AGILENT|KEYSIGHT)\s+TECHNOLOGIES|HEWLETT-PACKARD)\s*\,", response, flags=re.IGNORECASE)
        if match:
            self.mfr = match.group()
            match = re.search("(E3631|E3632|E3633|E3634)", response)
            if match:
                self.model = match.group()
            else:
                self.model = response.split(',')[1:4]
            self.logger.debug(self.mfr + " " + self.model)
            return True
        return False
    
    def reset(self):
        """Reset the instrument and set default configuration

        :return bool: True if instrument responed to Operation Complete query
        """
        if self.inst.query("*RST;*OPC?"):
            self.inst.write("*ESE 60;*SRE 48;*CLS;")
            return True
        else:
            return False
        
    def errorQuery(self):
        """Send an error query and return the results

        :return (int, str): Error code and string
        """
        err = self.inst.query(":SYST:ERR?")
        err = removeDelims(err)
        return (int(err[0]), " ".join(err[1:]))

    def setVoltage(self, voltage: float = 0, channel: int = 1) -> None:
        self.inst.write(f":INST:NSEL {channel};")
        self.inst.write(f":VOLT {voltage};")

    def setCurrentLimit(self, limit:float = 0, channel: int = 1):
        self.inst.write(f":INST:NSEL {channel};")
        self.inst.write(f":CURR {limit};")

    def setOutputEnable(self, enable: bool = False):
        self.inst.write(f":OUTP {1 if enable else 0};")

    def getVoltage(self, channel: int = 1) -> float:
        self.inst.write(f":INST:NSEL {channel};")
        result = self.inst.query(":MEAS:VOLT?")
        result = float(result.strip())
        return result

    def getCurrent(self, channel: int = 1) -> float:
        self.inst.write(f":INST:NSEL {channel};")
        result = self.inst.query(":MEAS:CURR?")
        result = float(result.strip())
        return result

    




