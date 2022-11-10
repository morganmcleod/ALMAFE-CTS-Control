from enum import Enum
import re
import pyvisa

class Channel(Enum):
    A = 0
    B = 1

class Unit(Enum):
    DBM = "DBM"
    W = "W"

class Trigger(Enum):
    IMMEDIATE = "IMM"
    BUS = "BUS"
    HOLD = "HOLD"
    EXTERNAL = "EXT"
    INTERNAL_A = "INT1"
    INTERNAL_B = "INT2"


class BaseE441X():

    DEFAULT_TIMEOUT = 15000

    def __init__(self, resource="GPIB0::13::INSTR", idQuery=True, reset=True):
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
        self.inst.close()

    def idQuery(self):
        mfr = None
        model = None
        response = self.inst.query("*IDN?")
        match = re.match("^\s*((AGILENT|KEYSIGHT)\s+TECHNOLOGIES|HEWLETT-PACKARD)\s*\,", response, flags=re.IGNORECASE)
        if match:
            mfr = match.group()
            match = re.search("(E4416A|E4417A|E4418B|E4419B|N1913A|N1914A)", response)
            if match:
                model = match.group()

        if mfr and model:
            self.twoChannel = model in ("E4417A", "E4419B", "N1914A")
            print(mfr + " " + model + (" two channel" if self.twoChannel else " one channel"))
            return True
        return False

    def reset(self):
        if self.inst.query("*RST;*OPC?"):
            self.inst.write("*CLS;*ESE 60;:STAT:OPER:NTR 65535;:FORM:READ:DATA ASC")
            return True
        else:
            return False

    def errorQuery(self):
        if self.inst.query("*ESR?"):
            return self.inst.query(":SYST:ERR?")
        else:
            return ""
             
    def zero(self, channel = Channel.A):
        if channel == Channel.B and not self.twoChannel:
            return False
        self.inst.timeout = 25000
        ret = self.inst.query(f"CAL{channel.value + 1}:ZERO:AUTO ONCE;*OPC?")
        self.inst.timeout = self.DEFAULT_TIMEOUT
        return True if ret else False

    def configureTrigger(self, trigger = Trigger.IMMEDIATE, channel = Channel.A, delayAutoState = True):
        if channel == Channel.B and not self.twoChannel:
            return False
        self.inst.write(f":TRIG{channel.value + 1}:DEL:AUTO {'ON' if delayAutoState else 'OFF'};")
        self.inst.write(f":TRIG{channel.value + 1}:SOUR {trigger.value}")
        return True

    def initiateContinuous(self, state = True, channel = Channel.A):
        if channel == Channel.B and not self.twoChannel:
            return False
        self.inst.write(f"INIT{channel.value + 1}:CONT {'ON' if state else 'OFF'};")
        return True

    def configureMeasurement(self, channel = Channel.A, resolution = 3, units = Unit.DBM):
        if channel == Channel.B and not self.twoChannel:
            return False
        m = channel.value + 1
        self.inst.write(f":CONF{m} DEF,{resolution},(@{m});:UNIT{m}:POW {units.value}")
        # for now this implementation covers way less than the LabVIEW equivalent
        return True

    def readMeasurement(self, channel = Channel.A):
        # read taking into account the configured Measurement
        if channel == Channel.B and not self.twoChannel:
            return False
        return float(self.inst.query(f"READ{channel.value + 1}?"))

    def readSingle(self, channel = Channel.A):
        # read instantaneous
        if channel == Channel.B and not self.twoChannel:
            return False
        return float(self.inst.query(f"FETC{channel.value + 1}:POW:AC?"))
        