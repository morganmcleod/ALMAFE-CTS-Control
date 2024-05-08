'''
Constants and interface liquid nitrogen cold load level controllers.
'''
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Tuple

from enum import Enum

class FillMode(Enum):
    # constants from AMI-1720 but should be sufficiently generic for other models
    UNKNOWN = -99
    NORMAL = 0
    AUTO_CHANGE = 1

class FillState(Enum):
    # constants from AMI-1720 but should be sufficiently generic for other models
    UNKNOWN = -99
    AUTO_OFF = 0
    AUTO_ON = 1
    FILLING = 3
    OPEN = 4
    CLOSED = 5
    TIMEOUT = 6

class ColdLoadState(BaseModel):
    fillMode: FillMode
    fillState: FillState
    fillModeText: str = ""
    fillStateText: str = ""
    level: float

class ColdLoadBase(ABC):

    def __init__(self, resource: str="", idQuery=True, reset=True):
        """Constructor

        :param str resource: VISA resource string
        :param bool idQuery: If true, perform an ID query and check compatibility, defaults to True
        :param bool reset: If true, reset the instrument and set default configuration, defaults to True
        """
        ok = True
        if ok and idQuery:
            ok = self.idQuery()
        if ok and reset:
            ok = self.reset()
        self.fillMode = self.getFillMode()
        self.fillState = self.getFillState()

    @abstractmethod
    def idQuery(self) -> bool:
        """Perform an ID query and check compatibility

        :return bool: True if the instrument is compatible with this class.
        """
        self.model = "ColdLoadBase"
        return True
    
    @abstractmethod
    def reset(self) -> bool:
        """Reset the instrument and set default configuration

        :return bool: True if reset succeeded
        """
        return True

    @abstractmethod
    def isConnected(self) -> bool:
        return True

    def startFill(self) -> None:
        """Start filling the cold load, with automatic stop when full
        """
        self.setFillState(FillState.AUTO_ON)

    def stopFill(self) -> None:
        """Stop and disable filling the cold load
        """
        self.setFillState(FillState.CLOSED)

    def shouldPause(self, 
            minLevel: float = 75, 
            maxLevel: float = 105, 
            enablePause: bool = True) -> Tuple[bool, str]:
        """Should the calling measurement procedure pause and wait for cold load intervention?

        :param float minLevel: Percent, defaults to 75
        :param float maxLevel: Percent, defaults to 105.  
            This is intended to catch very out-of-range readings from sensor problems.
        :param bool enablePause: If false generally return True = yes pause, except in error conditions.
        :return Tuple[bool, str]: Should pause?, and a description of why.
        """
        
        state = self.getFillState()
        level = self.getLevel()
        
        if state in (FillState.AUTO_OFF, FillState.AUTO_ON, FillState.FILLING, FillState.CLOSED, FillState.TIMEOUT):
            if level < minLevel or level > maxLevel:
                return enablePause, f"state is {state.name}, level is {level:.1f}%"
            else:
                return False, ""
        
        elif state == FillState.OPEN:
            if level < minLevel:
                return enablePause, f"state is {state.name}, level is {level:.1f}%"
            else:
                return False, ""
        
        else:
            return True, f"unsupported state {state.name}, level is {level:.1f}%"

    @abstractmethod
    def setFillMode(self, fillMode: FillMode) -> None:
        """Set the fill mode in a device-dependent way

        :param FillMode defined above
        """
        self.fillMode = fillMode

    @abstractmethod
    def getFillMode(self) -> FillMode:
        """Read the fillmode in a device-deptendent way

        :return FillMode defined above
        """
        return getattr(self, 'fillMode', FillMode.NORMAL)

    @abstractmethod
    def getLevel(self) -> float:
        """Read LN2 level in percent, device-dependent

        :return float: Percent
        """
        return 99.0
    
    @abstractmethod
    def setFillState(self, fillState: FillState) -> None:
        """Set the fill state in a device-dependent way

        :param FillState defined above
        """
        self.fillState = fillState
    
    @abstractmethod
    def getFillState(self) -> FillState:
        """Read the fill state in a device-dependent way

        :return FillState defined above
        """
        return self.fillState
