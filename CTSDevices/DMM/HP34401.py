import re
import pyvisa
import logging
from enum import Enum
from typing import List, Tuple, Optional

class Function(Enum):
    DC_VOLTAGE = "VOLT:DC"
    AC_VOLTAGE = "VOLT:AC"
    RESISTANCE_2_WIRE = "RES"
    RESISTANCE_4_WIRE = "FRES"
    DC_CURRENT = "CURR:DC"
    AC_CURRENT = "CURR:AC"
    FREQUENCY = "FREQ"
    PERIOD = "PER"
    CONTINUITY = "CONT"
    DIODE_CHECK = "DIOD"
    VDC_VDC_RATIO = "VOLT:DC:RAT"
    TEMPERATURE = "TEMP"
    CAPACITANCE = "CAP"

class TriggerSource(Enum):
    IMMEDIATE = "IMM"
    SOFTWARE = "BUS"
    EXTERNAL = "EXT"
    INTERNAL = "INT"

class TriggerSlope(Enum):
    NEGATIVE = "NEG"
    POSITIVE = "POS"

class SampleSource(Enum):
    TRIGGER_DELAY = "IMM"
    SAMPLE_INTERVAL = "TIM"

class AutoZero(Enum):
    OFF = "OFF"
    ON = "ON"
    ONCE = "ONCE"

class HP34401():

    DEFAULT_TIMEOUT = 10000

    VOLTAGE_RANGES = (1e-1, 1e+0, 1e+1, 1e+2, 1e+3)
    RESISTANCE_RANGES = (1e+2, 1e+3, 1e+4, 1e+5, 1e+6, 1e+7, 1e+8, 1e+9)
    CURRENT_RANGES = (1e-4, 1e-3, 1e-2, 1e-1, 1e+0, 3e+0)
    CAPACITANCE_RANGES = (1e-9, 1e-8, 1e-7, 1e-6, 1e-5)
    RESOLUTION_DIGITS = (4.5e+0, 5.5e+0, 6.5e+0)

    def __init__(self, resource="GPIB0::22::INSTR", idQuery=True, reset=True):
        """Constructor

        :param str resource: VISA resource string, defaults to "GPIB0::22::INSTR"
        :param bool idQuery: If true, perform an ID query and check compatibility, defaults to True
        :param bool reset: If true, reset the instrument and set default configuration, defaults to True
        """
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        rm = pyvisa.ResourceManager()
        self.inst = rm.open_resource(resource)
        self.inst.timeout = self.DEFAULT_TIMEOUT
        if self.inst.interface_type == pyvisa.constants.InterfaceType.asrl:
            self.inst.end_input = pyvisa.constants.termination_char
            self.inst.end_output = pyvisa.constants.termination_char
            self.inst.baud_rate = 9600
            self.inst.parity = pyvisa.constants.VI_ASRL_PAR_EVEN
            self.inst.data_bits = 7
            self.inst.stop_bits = pyvisa.constants.VI_ASRL_STOP_TWO
            self.inst.flow_control = pyvisa.constants.VI_ASRL_FLOW_DTR_DSR
            self.inst.flush(pyvisa.constants.VI_IO_IN_BUF_DISCARD | pyvisa.constants.VI_IO_OUT_BUF_DISCARD)
            self.inst.bytes_in_buffer = 4096
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
        self.model = None
        response = self.inst.query("*IDN?")
        match = re.search("(34401|34410|34411)", response)
        if match:
            self.model = match.group()
        if self.model:
            return True
        else:
            return False
    
    def reset(self) -> bool:
        """Reset the instrument and set default configuration

        :return bool: True if write succeeded
        """
        self.triggerConfigured = False
        self.multipointConfigured = False

        if self.inst.write("*RST"):
            return True
        else:
            return False
        
    def configureMeasurement(self, 
            function: Function, 
            autoRange: bool = True,
            manualResolution: float = 5.5, 
            manualRange: float = 1.0) -> None:

        command = f":CONF:{function.value}"
        if not autoRange:
            resolution = self.__upperBound(manualResolution, self.RESOLUTION_DIGITS)
            if function in (Function.DC_VOLTAGE, Function.AC_VOLTAGE):
                range = self.__upperBound(manualRange, self.VOLTAGE_RANGES)
            elif function in (Function.RESISTANCE_2_WIRE, Function.RESISTANCE_4_WIRE):
                range = self.__upperBound(manualRange, self.RESISTANCE_RANGES)
            elif function in (Function.DC_CURRENT, Function.AC_CURRENT):
                range = self.__upperBound(manualRange, self.CURRENT_RANGES)
            elif function == Function.CAPACITANCE:
                range = self.__upperBound(manualRange, self.CAPACITANCE_RANGES)
            else:
                # Autorange not supported for frequency, period, continuity, diode check, dc ratio, and temperature
                autoRange = True
        
        if not autoRange:
            command += f" {resolution}, {range};"
        else:
            command += ";"

        self.inst.write(command)
    
    def configureAveraging(self, function: Function, nPowerLineCycles: float = 1):
        self.inst.write(f":SENS:{function.value}:NPLCYCLES {nPowerLineCycles};")

    def configureAutoZero(self, autoZero: AutoZero = AutoZero.OFF):
        self.inst.write(f":SENS:ZERO:AUTO {autoZero.value}")

    def readSinglePoint(self) -> Optional[float]:
        if not self.triggerConfigured:
            self.configureTrigger(TriggerSource.IMMEDIATE)
        if not self.multipointConfigured:
            self.configureMultipoint(triggerCount = 1, sampleCount = 1)
        self.initiateMeasurement()
        result = None
        success = True
        
        while success and not result: 
            success, result = self.fetchMeasurement()
        if success:
            return result[0]
        else:
            return None

    def configureTrigger(self,
            triggerSource: TriggerSource,
            internalLevel: float = 0.0,
            slope: TriggerSlope = TriggerSlope.NEGATIVE,
            autoDelay: bool = True,
            manualDelay: float = 0.0) -> None:
        
        self.triggerSource = triggerSource

        command = f":TRIG:SOUR {triggerSource.value};"
        if autoDelay:
            command += ":TRIG:DEL:AUTO ON;"
        else:
            command += f":TRIG:DEL {manualDelay};"

        if self.model == "34410":
            command += f":TRIG:SLOP {slope.value};"
        elif self.model == "34411":
            command += f":TRIG:LEV {internalLevel}; TRIG:SLOP {slope.value};"

        self.inst.write(command)
        self.triggerConfigured = True

    def configureMultipoint(self,
            triggerCount: int = 1,
            sampleCount: int = 1,
            preTriggerSamples: int = 0,
            sampleInterval: float = 0.1,
            sampleSource: SampleSource = SampleSource.TRIGGER_DELAY) -> None:
        
        command = f":TRIG:COUN {triggerCount}; :SAMP:COUN {sampleCount};"
        if self.model == "34410":
            command += f":SAMP:TIM {sampleInterval};:SAMP:SOUR {sampleSource.value};"
        elif self.model == "34411":
            command += f":SAMP:TIM {sampleInterval};:SAMP:COUN:PRET {preTriggerSamples};:SAMP:SOUR {sampleSource.value};"

        self.inst.write(command)
        self.multipointConfigured = True

    def initiateMeasurement(self) -> None:
        if self.triggerSource == TriggerSource.SOFTWARE:
            command = "INIT;"
        else:
            command = "READ?"
        self.inst.write(command)

    def fetchMeasurement(self, timeout: int = 10000) -> Tuple[bool, List[float]]:
        if self.triggerSource == TriggerSource.SOFTWARE:                
            self.inst.write(":FETC?")
        try:
            response = self.inst.read().split(',')
            return True, [float(item) for item in response]
        except:
            return False, []

    def __upperBound(self, value: float, array: List[float]):
        """Find the first item in the sorted array which is greater than or equal to value.
        Returns the last value if not found"""

        i = 0
        success = False
        while not success and i < len(array):
            if array[i] >= value:
                success = True
            else:
                i += 1
        if success:
            return array[i]
        else:
            return array[-1]

