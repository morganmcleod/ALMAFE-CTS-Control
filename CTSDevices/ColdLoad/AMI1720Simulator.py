from .ColdLoadBase import ColdLoadBase, FillMode, FillState
from typing import Tuple
import time

class AMI1720Simulator(ColdLoadBase):

    DEFAULT_TIMEOUT = 2500
    
    def __init__(self, resource="TCPIP0::169.254.1.5::7180::SOCKET", idQuery=True, reset=True):
        """Constructor

        :param str resource: VISA resource string, defaults to "TCPIP0::169.254.1.5::7180::SOCKET"
        :param bool idQuery: If true, perform an ID query and check compatibility, defaults to True
        :param bool reset: If true, reset the instrument and set default configuration, defaults to True
        """
        self.setFillMode(FillMode.NORMAL_CH1)
        self.fillState = FillState.M_CLOSED

    def idQuery(self) -> bool:
        """Perform an ID query and check compatibility

        :return bool: True if the instrument is compatible with this class.
        """
        self.model = "AMI1720Simulator"
        return True
    
    def reset(self) -> bool:
        """Reset the instrument and set default configuration

        :return bool: True if write succeeded
        """
        return True
        
    def setFillMode(self, fillMode: FillMode):
        self.fillMode = fillMode

    def startFill(self):
        self.fillState = FillState.AUTO_ON

    def stopFill(self):
        self.fillState = FillState.M_CLOSED

    def checkLevel(self, minLevel: float = 25) -> Tuple[float, bool]:
        return 90.0, True

    def checkFillState(self) -> Tuple[bool, FillState, str]:
        return True, self.fillState, ""

    def waitForFill(self, minLevel: float = 25, timeoutSeconds: int = 0) -> Tuple[float, bool]:
        time.sleep(timeoutSeconds)
        return 90.0, True
