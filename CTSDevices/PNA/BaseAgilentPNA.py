from .PNAInterface import *
import re
import pyvisa

class Mode(Enum):
    CREATE = 0
    DELETE = 1
    SELECT = 2


class BaseAgilentPNA(PNAInterface):

    DEFAULT_TIMEOUT = 10000

    def __init__(self, resource="GPIB0::16::INSTR", idQuery=True, reset=True):
        rm = pyvisa.ResourceManager()
        self.inst = rm.open_resource(resource)
        self.inst.timeout = self.DEFAULT_TIMEOUT
        ok = True
        if ok and idQuery:
            ok = self.idQuery()
        if ok and reset:
            ok = self.reset()

    def idQuery(self, doPrint = False) -> bool:
        """Perform an ID query and check compatibility

        :return bool: True if the instrument is compatible with this class.
        """
        mfr = None
        model = None
        response = self.inst.query("*IDN?")
        match = re.match(r"^\s*(Agilent|Keysight)\s+Technologies\s*\,", response, flags=re.IGNORECASE)
        if match:
            mfr = match.group()
            match = re.search("(E8362A|E8362B|E8362C)", response)
            if match:
                model = match.group()

        if mfr and model:
            if doPrint:
                print(mfr + " " + model)
            return True
        return False

    def reset(self) -> bool:
        """Reset instrument to defaults

        :return bool: True if reset successful
        """
        if self.inst.query("SYST:PRES;*WAI;*OPC?"):
            self.inst.write(":STAT:OPER:DEV:ENAB 16;\n:STAT:OPER:DEV:PTR  16;\n*CLS")
            return True
        else:
            return False

    def configureMeasurementParameter(self, 
                                      mode: Mode, 
                                      meastType: MeasType, 
                                      channel: int = 1, 
                                      measName:str = "MY_MEAS"):
        """Create, delete, or select a measurement for a channel

        :param Mode mode: _description_
        :param MeasType meastType: _description_
        :param int channel: _description_, defaults to 1
        :param str measName: _description_, defaults to "MY_MEAS"
        """
        if mode == Mode.CREATE:
            self.inst.write(f":CALC{channel}:PAR:DEF \"{measName}\", {meastType.value};")
        elif mode == Mode.DELETE:
            self.inst.write(f":CALC{channel}:PAR:DEL \"{measName}\";")
        elif mode == Mode.SELECT:
            self.inst.write(f":CALC{channel}:PAR:SEL \"{measName}\";")

    def configureDisplayTrace(self, 
                              mode: Mode, 
                              displayWindow: int = 1,
                              displayTrace: int = 1,
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

    def checkDisplayWindow(self, displayWindow = 1):
        #TODO implement
        return True

    def configureDisplayWindow(self, mode:Mode, displayWindow = 1, displayTitle = "MY_DISPLAY"):
        #TODO implement
        return True

    def checkDisplayTrace(self, displayWindow: int = 1, displayTrace: int = 1):
        #TODO implement
        return True

