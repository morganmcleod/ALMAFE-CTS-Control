import re
import pyvisa
import logging
import time
from .schemas import *
from CTSDevices.Common.RemoveDelims import removeDelims
from CTSDevices.Common.VisaInstrument import VisaInstrument

class BaseMXA():
    """Base class for Agilent/Keysight MXA spectrum analyzers
    Provides common functionality available from all models.

    Only Swept SA mode is implemented!
    """
    DEFAULT_TIMEOUT = 10000

    def __init__(self, resource="TCPIP0::10.1.1.10::inst0::INSTR", idQuery=True, reset=True) -> None:
        """Constructor

        :param str resource: VISA resource string
        :param bool idQuery: If true, perform an ID query and check compatibility, defaults to True
        :param bool reset: If true, reset the instrument and set default configuration, defaults to True
        """
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.mfr = None
        self.model = None
        self.traceX = []
        self.traceY = []
        self.markerX = None
        self.markerY = None

        try:
            self.inst = VisaInstrument(resource, timeout = self.DEFAULT_TIMEOUT)                
            if self.inst.inst and self.inst.inst.session:
                self.inst.inst.flush(pyvisa.constants.VI_IO_IN_BUF_DISCARD | pyvisa.constants.VI_IO_OUT_BUF_DISCARD)
                done = True
        except:
            pass

        ok = self.isConnected()
        if ok and idQuery:
            ok = self.idQuery()
        if ok and reset:
            ok = self.reset()

    def __del__(self):
        """Destructor
        """
        self.inst.close()

    def isConnected(self) -> bool:
        if not self.inst.connected:
            return False
        try:
            result = self.inst.query("*ESR?")
            result = removeDelims(result)
            return len(result) > 0
        except:
            return False
        
    def idQuery(self):
        """Perform an ID query and check compatibility

        :return bool: True if the instrument is compatible with this class.
        """
        response = self.inst.query("*IDN?")
        match = re.match(r"^\s*(Agilent|Keysight)\s+Technologies\s*\,", response, flags=re.IGNORECASE)
        if match:
            self.mfr = match.group()
            match = re.search("(N9020A|N9010A|N9030A|N9000A|M9290A|N9000B|N9010B|N9020B|N9021B|N9030B|N9040B|N9041B|N9042B|N9048B|M9414A|M9411A|M9410A)", response)

            if match:
                self.model = match.group()

        # M9290A is the same as N9020A.
        if self.model == "M9290A":
            self.model = "N9020A"

        if self.mfr and self.model:
            return True
        return False

    def reset(self):
        """Reset the instrument and set default configuration

        :return bool: True if instrument responed to Operation Complete query
        """
        # HEADER OFF - instrument no longer returns headers with responses to queries
        # *ESE 61 - enables user request key, command error operation complete in event status register
        # *SRE 48 - enables message available, standard event bits in the status byte
        # *CLS - clears status
        opc = removeDelims(self.inst.query("*RST;*OPC?"))
        if opc and opc[0]:
            self.inst.write("*ESE 61;*SRE 48;*CLS;")
            self.inst.write(":INST:NSEL 1;:FORM ASC;")
            return True
        else:
            return False
        
    def errorQuery(self) -> tuple[int, str]:
        """Send an error query and return the results

        :return (int, str): Error code and string
        """
        err = self.inst.query(":SYST:ERR?", return_on_error = "-1,VISA Error")
        err = removeDelims(err)
        return int(err[0]), " ".join(err[1:])

    def configInternalPreamp(self, setting: InternalPreamp) -> tuple[bool, str]:
        # disable presel center:
        self.inst.write(f":POW:PADJ 0;")
        if setting == InternalPreamp.OFF:
            self.inst.write(":POW:GAIN:STAT OFF;")
        else:
            self.inst.write(f":POW:GAIN:STAT ON;:POW:GAIN:{setting.value};")
        # max mixer level -10:
        self.inst.write(":POW:MIX:RANG -10;")
        # standard uw path:
        if self.model == "N9030A":
            self.inst.write(":POW:MW:PATH STD;")
        code, msg = self.errorQuery()
        return code == 0, msg 

    def configAveraging(self, 
            count: int = 100,
            type: AveragingType = AveragingType.AUTO) -> tuple[bool, str]:

        if type == AveragingType.AUTO:
            self.inst.write(":AVER:TYPE:AUTO ON;")
        else:
            self.inst.write(f":AVER:TYPE {type.value};")
        self.inst.write(f":AVER:COUN {count};")
        code, msg = self.errorQuery()
        return code == 0, msg

    def configFreqStartStop(self, startHz: float, stopHz: float) -> tuple[bool, str]:
        self.inst.write(f":FREQ:START {startHz};:FREQ:STOP {stopHz};")
        code, msg = self.errorQuery()
        return code == 0, msg
    
    def configFreqCenterSpan(self, centerHz: float, spanHz: float) -> tuple[bool, str]:
        self.inst.write(f":FREQ:SPAN {spanHz};:FREQ:CENTER {centerHz};")
        code, msg = self.errorQuery()
        return code == 0, msg
    
    def configLevel(self, 
            refLevel: float = 0, 
            refLevelOffset: float = 0, 
            units: LevelUnits = LevelUnits.DBM,
            autoAtten: bool = True,
            manualAtten: float = 10) -> tuple[bool, str]:
        self.inst.write(f":UNIT:POW {units.value}")
        self.inst.write(f":DISP:WIND:TRAC:Y:RLEV {refLevel};:DISP:WIND:TRAC:Y:RLEV:OFFS {refLevelOffset};")
        if autoAtten:
            self.inst.write(":POW:ATT:AUTO ON;")
        else:
            self.inst.write(f":POW:ATT:AUTO OFF;:POW:ATT {manualAtten};")
        code, msg = self.errorQuery()
        return code == 0, msg
    
    def configAcquisition(self,
            continuous: bool = True,
            autoDetector: bool = True,
            manualDetector: DetectorMode = DetectorMode.NORMAL,
            traceNum: int = 1,
            logVertical: bool = True,        
            scalePerDiv: float = 10,
            sweepPoints: int = 1001) -> tuple[bool, str]:
        if autoDetector:
            self.inst.write(f":DET:TRAC{traceNum}:AUTO ON;")
        else:
            self.inst.write(f":DET:TRAC{traceNum}:AUTO OFF;:DET:TRAC{traceNum} {manualDetector.value};")
        self.inst.write(f":SWE:POIN {sweepPoints};")
        if logVertical:
            self.inst.write(f":DISP:WIND:TRAC:Y:SPAC LOG;:DISP:WIND:TRAC:Y:PDIV {scalePerDiv};")
        else:
            self.inst.write(":DISP:WIND:TRAC:Y:SPAC LIN;")
        self.inst.write(f":INIT:CONT {'ON' if continuous else 'OFF'};")
        code, msg = self.errorQuery()
        return code == 0, msg

    def configSweepCoupling(self,
            autoResolutionBW: bool = True,
            resolutionBW: float = 3e6,
            autoVideoBW: bool = True,
            videoBW: float = 3e6,
            autoSweepTime: bool = True,
            sweepTime: float = 0.0663,
            autoVBWRBWRatio: bool = False,
            VBWRBWRatio: float = 1) -> tuple[bool, str]:
        
        if autoVBWRBWRatio:
            self.inst.write(":BWID:VID:RAT:AUTO ON;")
        else:
            self.inst.write(f":BWID:VID:RAT:AUTO OFF;:BWID:VID:RAT {VBWRBWRatio};")
        if autoSweepTime:
            self.inst.write(":SWE:TIME:AUTO ON;")
        else:
            self.inst.write(f":SWE:TIME:AUTO OFF;:SWE:TIME {sweepTime};")
        if autoResolutionBW:
            self.inst.write(":BWID:AUTO ON;")
        else:
            self.inst.write(f":BWID:AUTO OFF;:BWID {resolutionBW};")
        if autoVideoBW:
            self.inst.write(":BWID:VID:AUTO ON;")
        else:
            self.inst.write(f":BWID:VID:AUTO OFF;:BWID:VID {videoBW};")
        code, msg = self.errorQuery()
        return code == 0, msg

    def configTraceType(self,
            traceNum: int = 1,
            type: TraceType = TraceType.CLEAR_WRITE,
            enableUpdate: bool = True,
            enableDisplay: bool = True) -> tuple[bool, str]:

        self.inst.write(f":TRAC{traceNum}:TYPE {type.value};")
        self.inst.write(f":TRAC{traceNum}:UPD {'ON' if enableUpdate else 'OFF'};")
        self.inst.write(f":TRAC{traceNum}:DISP {'ON' if enableDisplay else 'OFF'};")
        code, msg = self.errorQuery()
        return code == 0, msg
    
    def configDetector(self,
            autoDetector: bool = True,
            detector: DetectorMode = DetectorMode.AVERAGE,
            autoRefChannel: bool = True,
            refChannel: DetectorMode = DetectorMode.AVERAGE) -> tuple[bool, str]:
        if autoDetector:
            self.inst.write(":SEM:DET:OFFS:AUTO ON;")
        else:
            self.inst.write(f":SEM:DET:OFFS:AUTO OFF;:SEM:DET:OFFS {detector.value};")
        if autoRefChannel:
            self.inst.write(":SEM:DET:CARR:AUTO ON;")
        else:
            self.inst.write(f":SEM:DET:CARR:AUTO OFF;:SEM:DET:CARR {refChannel.value};")
        code, msg = self.errorQuery()
        return code == 0, msg

    def configMarkerType(self,
            markerNum: int = 1,
            type: MarkerType = MarkerType.NORMAL,
            readout: MarkerReadout = MarkerReadout.AUTO,
            refMarkerNum: int = 12,
            autoGateTime: bool = True,
            gateTime: float = 0.1,
            enableFreqCounter: bool = False) -> tuple[bool, str]:
        
        self.inst.write(f":CALC:MARK{markerNum}:MODE {type.value};")
        if type == MarkerType.DELTA:
            self.inst.write(f":CALC:MARK{markerNum}:REF {refMarkerNum};")
        if readout == MarkerReadout.AUTO:
            self.inst.write(f"CALC:MARK{markerNum}:X:READ:AUTO ON;")
        else:
            self.inst.write(f"CALC:MARK{markerNum}:X:READ {readout.value};")
        self.inst.write(f":CALC:MARK{markerNum}:FCO {'ON' if enableFreqCounter else 'OFF'};")
        if autoGateTime:
            self.inst.write(f":CALC:MARK{markerNum}:FCO:GAT:AUTO ON;")
        else:
            self.inst.write(f":CALC:MARK{markerNum}:FCO:GAT:AUTO OFF;:CALC:MARK{markerNum}:FCO:GAT {gateTime};")
        code, msg = self.errorQuery()
        return code == 0, msg
            
    def configSmoothing(self, traceNum:int = 1, numPoints: int = 1) -> tuple[bool, str]:
        self.inst.write(f":TRAC:MATH:SMO TRACE{traceNum};:TRAC:MATH:SMO:POIN {numPoints};")
        code, msg = self.errorQuery()
        return code == 0, msg

    def restartTrace(self) -> tuple[bool, str]:
        self.inst.write(":INIT:REST;")
        code, msg = self.errorQuery()
        return code == 0, msg

    def readTrace(self, traceNum:int = 1, timeout: int = 30) -> tuple[bool, str]:
        self.inst.write(":INIT:SAN;")
        self.inst.write("*CLS;*OPC;")
        start = time.time()
        done = False
        error = False
        while not done and not error:
            elapsed = time.time() - start
            if elapsed > timeout:
                error = True
            else:
                ret = removeDelims(self.inst.query("*STB?"), delimsRe = r'[;,"\s\r\n]')
                try:
                    if int(ret[0]) & 32:
                        done = True
                except:
                    error = True
            time.sleep(0.01)
        if error:
            return False, "Timeout or error waiting for spectrum analyzer acqisition"
        ret = self.inst.query(f":FETC:SAN{traceNum}?;")
        if not ret:
            return False, "Timeout or error reading spectrum analyzer trace"
        ret = removeDelims(ret)
        ret = [float(x) for x in ret]
        self.traceX = ret[0::2]
        self.traceY = ret[1::2]
        code, msg = self.errorQuery()
        return code == 0, msg

    def readMarker(self, markerNum: int = 1) -> tuple[bool, str]:
        ret = self.inst.query(f":CALC:MARK{markerNum}:X?;:CALC:MARK{markerNum}:Y?;")
        ret = removeDelims(ret, delimsRe = r'[;,"\s\r\n]')
        ret = [float(x) for x in ret]
        self.markerX = ret[0]
        self.markerY = ret[1]
        code, msg = self.errorQuery()
        return code == 0, msg
