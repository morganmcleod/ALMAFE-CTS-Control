from ..Common.RemoveDelims import removeDelims
from .schemas import Channel, Trigger, Unit
import re
import pyvisa

class BaseE441X():
    """Base class for Agilent/Keysight Power Meters E441xA, E441xB, N191xA
    Provides common functionality available from all models.
    """

    DEFAULT_TIMEOUT = 15000
    
    def __init__(self, resource="GPIB0::13::INSTR", idQuery=True, reset=True):
        """Constructor

        :param str resource: VISA resource string, defaults to "GPIB0::13::INSTR"
        :param bool idQuery: If true, perform an ID query and check compatibility, defaults to True
        :param bool reset: If true, reset the instrument and set default configuration, defaults to True
        """
        rm = pyvisa.ResourceManager()
        self.inst = rm.open_resource(resource)
        self.inst.timeout = self.DEFAULT_TIMEOUT
        self.twoChannel = False
        if self.inst.interface_type == pyvisa.constants.InterfaceType.asrl:
            self.inst.end_input = pyvisa.constants.termination_char
            self.inst.end_output = pyvisa.constants.termination_char
            self.inst.write(":SYST:COMM:SER:TRAN:ECHO\sOFF")
        ok = True
        if ok and idQuery:
            ok = self.idQuery()
        if ok and reset:
            ok = self.reset()

    def __del__(self):
        """Destructor
        """
        self.inst.close()

    def idQuery(self, doPrint = False):
        """Perform an ID query and check compatibility

        :return bool: True if the instrument is compatible with this class.
        """
        mfr = None
        model = None
        response = self.inst.query("*IDN?")
        match = re.match(r"[ ]*((AGILENT|KEYSIGHT)\s+TECHNOLOGIES|HEWLETT-PACKARD)\s*\,", response, flags=re.IGNORECASE)
        if match:
            mfr = match.group()
            match = re.search("(E4416A|E4417A|E4418B|E4419B|N1913A|N1914A)", response)
            if match:
                model = match.group()

        if mfr and model:
            self.twoChannel = model in ("E4417A", "E4419B", "N1914A")
            # check whether sensor 2 is connected:
            if self.twoChannel and not int(self.inst.query("STAT:DEV:COND?")) & 4:
                self.twoChannel = False
            if doPrint:
                print(mfr + " " + model + (", two channel" if self.twoChannel else ", one channel"))
            return True
        return False

    def reset(self):
        """Reset the instrument and set default configuration

        :return bool: True if instrument responed to Operation Complete query
        """
        if self.inst.query("*RST;*OPC?"):
            self.inst.write("*CLS;*ESE 60;:STAT:OPER:NTR 65535;:FORM:READ:DATA ASC")
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

    def zero(self, channel = Channel.A):
        """Zero the power meter

        :param Channel channel: which channel to zero, defaults to Channel.A
        :return bool: True if instrument responed to Operation Complete query
        """
        if channel == Channel.B and not self.twoChannel:
            return False
        self.inst.timeout = 25000
        ret = self.inst.query(f"CAL{channel.value + 1}:ZERO:AUTO ONCE;*OPC?")
        self.inst.timeout = self.DEFAULT_TIMEOUT
        return True if ret else False

    def setOutputRef(self, enable:bool):
        """Enable/disable the power ref output: 50 MHz at 0 dBm

        :param bool enable
        :return bool: True if instrument responed to Operation Complete query
        """
        self.inst.write(f"OUTP:ROSC {'ON' if enable else 'OFF'}")
        ret = self.inst.query("*OPC?")
        return True if ret else False

    def configureTrigger(self, trigger = Trigger.IMMEDIATE, channel = Channel.A, delayAutoState = True):
        """Configure power meter triggering

        :param trigger mode, defaults to Trigger.IMMEDIATE
        :param Channel channel: whichc channel to configure, defaults to Channel.A
        :param bool delayAutoState: whether or not there is a settling-time delay before measurement, defaults to True
        :return bool: True if instrument responed to Operation Complete query
        """
        if channel == Channel.B and not self.twoChannel:
            return False
        self.inst.write(f":TRIG{channel.value + 1}:DEL:AUTO {'ON' if delayAutoState else 'OFF'};")
        self.inst.write(f":TRIG{channel.value + 1}:SOUR {trigger.value}")
        ret = self.inst.query("*OPC?")
        return True if ret else False

    def initContinuous(self, state = True, channel = Channel.A):
        """Initiate Continuous: set the instrument for either single or contiunous trigger cycles

        :param bool state: If true trigger continuously, defaults to True
        :param Channel channel: which channel to configure, defaults to Channel.A
        :return bool: True if instrument responed to Operation Complete query
        """
        if channel == Channel.B and not self.twoChannel:
            return False
        self.inst.write(f"INIT{channel.value + 1}:CONT {'ON' if state else 'OFF'};")
        ret = self.inst.query("*OPC?")
        return True if ret else False

    def configMeasurement(self, channel = Channel.A, resolution = 3, units = Unit.DBM):
        """Configure measurement options.
        TODO: for now this implementation covers way less than the LabVIEW equivalent

        :param Channel channel: which channel to configure, defaults to Channel.A
        :param int resolution: number of decimal places, defaults to 3
        :param Unit units, defaults to Unit.DBM
        :return bool: True if instrument responed to Operation Complete query
        """
        if channel == Channel.B and not self.twoChannel:
            return False
        m = channel.value + 1
        self.inst.write(f":CONF{m} DEF,{resolution},(@{m});:UNIT{m}:POW {units.value}")
        ret = self.inst.query("*OPC?")
        return True if ret else False

    def read(self, channel = Channel.A):
        """Read the instrument once, taking into account the configured Measurement

        :param Channel channel: which channel to measure, defaults to Channel.A
        :return float: measured power level
        """
        if channel == Channel.B and not self.twoChannel:
            return False
        return float(self.inst.query(f"READ{channel.value + 1}?"))

    def simpleRead(self, channel = Channel.A):
        """Read the instrument when it is running in continuous mode

        :param Channel channel: which channel to measure, defaults to Channel.A
        :return float: measured power level
        """
        if channel == Channel.B and not self.twoChannel:
            return False
        return float(self.inst.query(f"FETC{channel.value + 1}:POW:AC?"))
