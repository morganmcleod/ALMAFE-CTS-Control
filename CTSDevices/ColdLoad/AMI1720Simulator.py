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
        self.setFillMode(FillMode.NORMAL)
        self.fillState = FillState.CLOSED

    def idQuery(self) -> bool:
        """Perform an ID query and check compatibility

        :return bool: True if the instrument is compatible with this class.
        """
        self.model = "AMI1720Simulator"
        return True
    
    def reset(self) -> bool:
        """Reset the instrument and set default configuration

        :return bool: True if reset succeeded
        """
        return True
        
    def setFillMode(self, fillMode: FillMode) -> None:
        """Set the fill mode in a device-dependent way

        :param FillMode defined above
        """
        self.fillMode = fillMode

    def getFillMode(self) -> FillMode:
        """Read the fillmode in a device-deptendent way

        :return FillMode defined above
        """
        return getattr(self, 'fillMode', FillMode.NORMAL)
    
    def getLevel(self) -> float:
        """Read LN2 level in percent, device-dependent

        :return float: Percent
        """
        return 99.0
    
    def setFillState(self, fillState: FillState) -> None:
        """Set the fill state in a device-dependent way

        :param FillState defined above
        """
        self.fillState = fillState

    def getFillState(self) -> FillState:
        """Read the fill state in a device-dependent way

        :return FillState defined above
        """
        return self.fillState
