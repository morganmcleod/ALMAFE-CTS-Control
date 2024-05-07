import re
import pyvisa
from pyvisa.constants import BufferOperation
import logging
from CTSDevices.Common.RemoveDelims import removeDelims
from .ColdLoadBase import ColdLoadBase, FillMode, FillState
from threading import Lock

class AMI1720(ColdLoadBase):

    DEFAULT_TIMEOUT = 2500
    
    def __init__(self, resource="TCPIP0::10.1.1.5::7180::SOCKET", idQuery=True, reset=True):
        """Constructor

        :param str resource: VISA resource string, defaults to "TCPIP0::169.254.1.5::7180::SOCKET"
        :param bool idQuery: If true, perform an ID query and check compatibility, defaults to True
        :param bool reset: If true, reset the instrument and set default configuration, defaults to True
        """
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.lock = Lock()
        rm = pyvisa.ResourceManager()
        self.inst = rm.open_resource(resource)
        self.inst.timeout = self.DEFAULT_TIMEOUT
        self.inst.read_termination = '\n'
        self.inst.write_termination = '\n'
        ok = True
        if ok and idQuery:
            ok = self.idQuery()
        if ok and reset:
            ok = self.reset()            
        self.fillMode = self.getFillMode()
        self.fillState = self.getFillState()

    def __del__(self):
        """Destructor
        """
        self.inst.close()

    def idQuery(self) -> bool:
        """Perform an ID query and check compatibility

        :return bool: True if the instrument is compatible with this class.
        """
        self.model = None
        with self.lock:
            
            response = self.inst.query("*IDN?")
        match = re.search("MODEL 1720", response)
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
        # TODO implement?
        # manual says *RST Performs a Factory Restore if a restore file is available. All prior settings are lost!
        return True
        
    def setFillMode(self, fillMode: FillMode) -> None:
        """Set the fill mode in a device-dependent way

        :param FillMode defined above
        """
        self.fillMode = fillMode
        with self.lock:            
            if self.fillMode == FillMode.AUTO_CHANGE:
                self.inst.write("FILL:MODE AUTOCH")
            else:
                self.inst.write("FILL:MODE NORMAL")

    def getFillMode(self) -> FillMode:
        """Read the fillmode in a device-deptendent way

        :return FillMode defined above
        """
        mode = None
        with self.lock:            
            response = self.inst.query("FILL:MODE?")
        self.logger.debug(f"FILL:MODE? -> '{response}'")
        response = removeDelims(response)
        if len(response) < 2:
            with self.lock:
                response = self.inst.read()
            self.logger.debug(f" -> '{response}'")
            response = removeDelims(response)
        if len(response) == 2:
            mode = FillMode(int(response[0]))
        if mode is not None:
            return mode
        else:
            return FillMode.UNKNOWN

    def getLevel(self) -> float:
        """Read LN2 level in percent, device-dependent

        :return float: Percent
        """
        level = None
        with self.lock:                
            response = self.inst.query("MEAS:CH1:LEV?")
        self.logger.debug(f"MEAS:CH1:LEV? -> '{response}'")
        response = removeDelims(response)
        if len(response) < 1:
            with self.lock:
                response = self.inst.read()
            self.logger.debug(f" -> '{response}'")
            response = removeDelims(response)
        if len(response) == 1:
            level = float(response[0])
        if level is not None:
            return level
        else:
            return -1.0
    
    def setFillState(self, fillState: FillState) -> None:
        """Set the fill state in a device-dependent way

        :param FillState defined above
        """
        with self.lock:
            
            self.inst.write(f"CONF:FILL:CH1:STA {fillState.value}")
    
    def getFillState(self) -> FillState:
        """Read the fill state in a device-dependent way

        :return FillState defined above
        """
        state = None
        with self.lock:
            response = self.inst.query("FILL:CH1:STA?")
        self.logger.debug(f"FILL:CH1:STA? -> '{response}'")
        response = removeDelims(response)
        if len(response) < 2:
            with self.lock:
                response = self.inst.query("FILL:CH1:STA?")
            self.logger.debug(f" -> '{response}'")
            response = removeDelims(response)
        if len(response) == 2:
            state = FillState(int(response[0]))
        if state is not None:
            return state
        else:
            return FillState.UNKNOWN
