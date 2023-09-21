from .Interface import SignalGenInterface
from ..Common.RemoveDelims import removeDelims
import re
import pyvisa
import logging

class SignalGenerator(SignalGenInterface):

    DEFAULT_TIMEOUT = 10000

    def __init__(self, resource="GPIB0::19::INSTR", idQuery=True, reset=True):
        """Constructor

        :param str resource: VISA resource string, defaults to "GPIB0::13::INSTR"
        :param bool idQuery: If true, perform an ID query and check compatibility, defaults to True
        :param bool reset: If true, reset the instrument and set default configuration, defaults to True
        """
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        rm = pyvisa.ResourceManager()
        try:
            self.inst = rm.open_resource(resource)
            self.inst.timeout = self.DEFAULT_TIMEOUT
            ok = True
            if ok and idQuery:
                ok = self.idQuery()
            if ok and reset:
                ok = self.reset()
        except pyvisa.VisaIOError as err:
            self.logger.error(err)
            self.inst = None

    def __del__(self):
        """Destructor
        """
        if self.inst:
            self.inst.close()
            self.inst = None

    def idQuery(self):
        """Perform an ID query and check compatibility

        :return bool: True if the instrument is compatible with this class.
        """
        if not self.inst:
            return False

        mfr = None
        model = None
        response = self.inst.query("*IDN?")
        match = re.match(r"[ ]*((AGILENT|KEYSIGHT)\s+TECHNOLOGIES)\s*\,", response, flags=re.IGNORECASE)
        if match:
            mfr = match.group()
            match = re.search("(N5181A|N5182A|N5183A|N5161A|N5162A|E8241A|E8244A|E8251A|E8254A|E8247C|E8257C|E8267C|E8257D|E8267D|N5171B|N5172B|N5181B|N5182B|N5173B|N5183B)", response)
            if match:
                model = match.group()

        if mfr and model:
            self.logger.debug(mfr + " " + model)
            return True
        return False

    def reset(self):
        """Reset the instrument and set default configuration

        :return bool: True if instrument responed to Operation Complete query
        """
        if not self.inst:
            return False

        if self.inst.query("*RST;*OPC?"):
            self.inst.write("*ESE 61;*SRE 48;*CLS;")
            # *ESE 61 enables the mask on the Standard Event Status Enable register for
            # Operation Complete, Query Error, Device Error, Execution Error and Command
            # Error.
            # *SRE 48 enables the mask on the Service Request Enable register for Message,
            # Status Summary.
            # *CLS clears the Status Byte register and all event registers.
            return True
        else:
            return False

    def errorQuery(self):
        """Send an error query and return the results

        :return (int, str): Error code and string
        """
        if not self.inst:
            return (None, "No connection")
        try:
            err = self.inst.query(":SYST:ERR?")
            err = removeDelims(err)
            return (int(err[0]), " ".join(err[1:]))            
        except pyvisa.VisaIOError as err:
            self.inst.close()
            self.inst = None
            return (None, err.abbreviation)

    def isConnected(self) -> bool:
        if not self.inst:
            return False
        code, _ = self.errorQuery()
        return True if code is not None else False

    def setAmplitude(self, amp_dB:float) -> bool:
        if self.inst:
            self.inst.write(f":POW:LEV {amp_dB:.4f} DBM")
            return True
        else:
            return False

    def setFrequency(self, freq_GHz:float) -> bool:
        if self.inst:
            self.inst.write(f":FREQ:FIX {freq_GHz} GHZ")
            return True
        else:
            return False

    def setRFOutput(self, enable:bool) -> bool:
        if self.inst:
            self.inst.write(f":OUTP:STAT {'ON' if enable else 'OFF'}")
            return True
        else:
            return False

    def getAmplitude(self) -> float:
        if self.inst:
            result = self.inst.query(":POW:LEV?")
            return float(result)
        else:
            return -99

    def getFrequency(self) -> float:
        if self.inst:
            result = self.inst.query(":FREQ:FIX?")
            return float(result) / 1e9
        else:
            return 0

    def getRFOutput(self) -> bool:
        if self.inst:
            result = self.inst.query(":OUTP:STAT?")
            return int(result) != 0
        else:
            return False

