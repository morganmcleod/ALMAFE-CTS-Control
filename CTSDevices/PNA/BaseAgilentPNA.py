from .PNAInterface import *
from .schemas import *
from typing import Tuple, List, Optional
from CTSDevices.Common.RemoveDelims import removeDelims
import re
import pyvisa
import time
import logging

class BaseAgilentPNA(PNAInterface):

    DELIMS_KEEP_COMMA = r'["\s\r\n]'
    DEFAULT_TIMEOUT = 10000

    def __init__(self, resource="GPIB0::16::INSTR", idQuery=True, reset=True):
        self.logger = logging.getLogger()
        rm = pyvisa.ResourceManager()
        self.inst = rm.open_resource(resource)
        self.inst.timeout = self.DEFAULT_TIMEOUT
        ok = True
        if ok and idQuery:
            ok = self.idQuery()
        if ok and reset:
            ok = self.reset()

    def idQuery(self) -> Optional[str]:
        """Perform an ID query and check compatibility
        :return str: manufacturer and model or None
        """
        mfr = None
        model = None
        response = self.inst.query("*IDN?")
        match = re.match(r"^\s*(Agilent|Keysight)\s+Technologies\s*\,", response, flags=re.IGNORECASE)
        if match:
            mfr = match.group()
            match = re.search("(E8361A|E8362A|E8363A|E8364A|E8362B|E8363B|E8364B|E8362C)", response)
            if match:
                model = match.group()

        if mfr and model:
            ret = mfr + " " + model
            self.logger.debug(ret)
            return ret
        return None

    def errorQuery(self) -> Tuple[int, str]:
        err = self.inst.query(":SYST:ERR?")
        err = removeDelims(err)
        return (int(err[0]), " ".join(err[1:]))
        
    def reset(self) -> bool:
        """Reset instrument to defaults

        :return bool: True if reset successful
        """
        if self.inst.query("SYST:PRES;*WAI;*OPC?"):
            self.inst.write(":STAT:OPER:DEV:ENAB 16;\n:STAT:OPER:DEV:PTR 16;\n*CLS")
            return True
        else:
            return False

    def listMeasurementParameters(self, channel:int = 1):
        measNames = removeDelims(self.inst.query(f":CALC{channel}:PAR:CAT?;"))
        self.logger.debug(measNames)
        if measNames == ['NO', 'CATALOG']:
            measNames = []
        return measNames

    def configureMeasurementParameter(self, 
                                      channel:int = 1, 
                                      mode:Mode = Mode.CREATE,
                                      measType:MeasType = None, 
                                      measName:str = "MY_MEAS"):
        """Create, delete, or select a measurement for a channel

        :param int channel: _description_, defaults to 1
        :param Mode mode: _description_
        :param MeasType measType: _description_
        :param str measName: _description_, defaults to "MY_MEAS"
        """
        if mode == Mode.CREATE:
            self.inst.write(f":CALC{channel}:PAR:DEF \"{measName}\", {measType.value};")
        elif mode == Mode.DELETE:
            self.inst.write(f":CALC{channel}:PAR:DEL \"{measName}\";")
        elif mode == Mode.SELECT:
            self.inst.write(f":CALC{channel}:PAR:SEL \"{measName}\";")

    def checkDisplayTrace(self, displayWindow:int = 1, displayTrace:int = 1):
        response = removeDelims(self.inst.query(f"DISP:WIND{displayWindow}:CAT?"))
        return str(displayTrace) in response

    def configureDisplayTrace(self, 
                              mode:Mode, 
                              displayWindow:int = 1,
                              displayTrace:int = 1,
                              measName:str = "MY_MEAS"):
        """Create or delete a displayed trace

        :param Mode mode: _description_
        :param int displayWindow: _description_, defaults to 1
        :param int displayTrace: _description_, defaults to 1
        :param str measName: _description_, defaults to "MY_MEAS"
        """
        if mode == Mode.CREATE:
            # if the window doesn't exist, create it:
            if not self.checkDisplayWindow(displayWindow):
                self.configureDisplayWindow(Mode.CREATE, displayWindow)
            # if the trace already exists, delete it:
            if self.checkDisplayTrace(displayWindow, displayTrace):
                self.inst.write(f":DISP:WIND{displayWindow}:TRAC{displayTrace}:DEL;")
            # create the trace:
            self.inst.write(f":DISP:WIND{displayWindow}:TRAC{displayTrace}:FEED \"{measName}\";")
        elif mode == Mode.DELETE:
            self.inst.write(f":DISP:WIND{displayWindow}:TRAC{displayTrace}:DEL;")

    def configureSweep(self, 
                       channel:int = 1,
                       sweepType:SweepType = SweepType.LIN_FREQ,
                       sweepGenType:SweepGenType = SweepGenType.ANALOG,
                       sweepOrDwellTime:float = 6.03,
                       sweepPoints:int = 201,
                       sweepTimeAuto:bool = True):
        cmd = f":SENS{channel}:SWE:TYPE {sweepType.value};GEN {sweepGenType.value};"
        if sweepType != SweepType.SEGMENT_SWEEP:
            cmd += f"POIN {sweepPoints};"

        timeCmd = 'TIME' if sweepGenType==SweepGenType.ANALOG else 'DWEL'
        cmd += f"{timeCmd}:AUTO {'ON' if sweepTimeAuto else 'OFF'};"
        if not sweepTimeAuto:
            cmd += f":SENS{channel}:SWE:{timeCmd} {sweepOrDwellTime:.6f};"
        self.inst.write(cmd)

    def checkDisplayWindow(self, displayWindow = 1):
        response = removeDelims(self.inst.query(r":DISP:CAT?"))
        return str(displayWindow) in response

    def configureDisplayWindow(self, mode:Mode, displayWindow = 1, displayTitle = "MY_DISPLAY"):
        if mode == Mode.CREATE:
            titleCommand = "ON" if len(displayTitle) else "OFF"
            self.inst.write(f""":DISP:WIND{displayWindow} ON;
                                :DISP:WIND{displayWindow}:TITL:DATA \"{displayTitle}\";
                                :DISP:WIND{displayWindow}:TITL {titleCommand};""")
        elif mode == Mode.DELETE:
            self.inst.write(f":DISP:WIND{displayWindow} OFF;")


    def configureBandwidth(self, channel:int = 1, bandWidthHz:float = 20e3):
        self.inst.write(f":SENS{channel}:BAND {bandWidthHz:.6f};")

    def configureFreqCenterSpan(self, channel:int = 1, centerFreq_Hz:float = 1.5015e9, spanFreq_Hz:float = 2.9997e9):
        self.inst.write(f":SENS{channel}:FREQ:CENT {centerFreq_Hz};SPAN {spanFreq_Hz};")

    def setTriggerSweepSignal(self, source:TriggerSource = TriggerSource.IMMEDIATE,
                                    scope:TriggerScope = TriggerScope.ALL_CHANNELS,
                                    level:TriggerLevel = TriggerLevel.LOW,
                                    delaySeconds:float = 0.0):
        self.inst.write(f":TRIG:SOUR {source.value};:TRIG:SCOP {scope.value};")
        if source == TriggerSource.EXTERNAL:
            self.inst.write(f":TRIG:LEV {level.value};DEL {delaySeconds};")
        self.inst.write("*CLS")

    def configureTriggerChannel(self, channel:int = 1, 
                                      triggerPoint:bool = True, 
                                      mode:TriggerMode = TriggerMode.CONTINUOUS,
                                      count:int = 1):
        self.inst.write(f":SENS{channel}:SWE:TRIG:POIN {'ON' if triggerPoint else 'OFF'};")
        if mode == TriggerMode.COUNT:
            self.inst.write(f":SENS{channel}:SWE:GRO:COUN {count};")
        self.inst.write(f":SENS{channel}:SWE:MODE {mode.value};")

    def configurePowerAttenuation(self, channel:int = 1, attenuation:float = 0.0):
        self.inst.write(f":SOUR{channel}:POW:ATT {attenuation};")

    def configurePowerLevel(self, channel:int = 1, level:float = 0.0):
        self.inst.write(f":SOUR{channel}:POW {level};")

    def configurePowerState(self, rfPowerState:bool = True):
        self.inst.write(f":OUTP {'ON' if rfPowerState else 'OFF'};")

    def generateTriggerSignal(self, channel:int = 1, mode:bool = True):
        if mode:
            self.inst.write(f"*CLS;:INIT{channel};")
        else:
            self.inst.write(":ABOR;")

    def checkSweepComplete(self, waitForComplete:bool = True, timeoutSec:float = 20.0) -> bool:
        complete = False
        startTime = time.time()
        while not complete:
            time.sleep(.020)
            result = removeDelims(self.inst.query(":STAT:OPER:DEV?"))
            if int(result[0]):
                complete = True
            elif not waitForComplete:
                break
            elif time.time() - startTime > timeoutSec:
                break
        return complete

    def setDataFormat(self, format:DataFormat = DataFormat.REAL32, order:DataOrder = DataOrder.NORMAL):
        self.inst.write(f":FORM:DATA {format.value};BORD {order.value};")

    def getDataFormat(self):
        format = removeDelims(self.inst.query(":FORM:DATA?;"), self.DELIMS_KEEP_COMMA)
        if format[0] == "REAL,+32":
            return DataFormat.REAL32
        elif format[0] == "REAL,+64":
            return DataFormat.REAL64
        elif format[0] == "ASC,+0":
            return DataFormat.ASCII
        else:
            return None

    def readData(self, channel:int = 1, 
                       format:Format = Format.FDATA, 
                       sampleCount:int = 401, 
                       measName:str = "MY_MEAS"):
        self.configureMeasurementParameter(channel, Mode.SELECT, measName = measName)
        self.setDataFormat(DataFormat.REAL32)
        trace = self.inst.query_binary_values(f"CALC{channel}:DATA? {format.value};", datatype='f', is_big_endian = True)
        if trace:
            return trace
        else:
            return None


