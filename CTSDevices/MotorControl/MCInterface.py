'''
Data models and interface for three-axis motor controller
'''
from .schemas import MotorStatus, Position, MoveStatus
from abc import ABC, abstractmethod

class MCError(Exception):
    def __init__(self, *args):
        super(MCError, self).__init__(*args)

class MCInterface(ABC):

    @abstractmethod
    def isConnected(self) -> bool:
        pass

    @abstractmethod
    def setXYSpeed(self, speed:float):
        '''
        speed: mm/second
        '''
        pass

    @abstractmethod
    def getXYSpeed(self) -> float:
        pass

    @abstractmethod
    def setXYAccel(self, accel:float):
        '''
        accel mm/sec^2
        '''
        pass

    @abstractmethod
    def setXYDecel(self, decel:float):
        '''
        decel mm/sec^2
        '''
        pass
    
    @abstractmethod
    def setPolSpeed(self, speed:float):
        '''
        speed: degrees/second
        '''
        pass

    @abstractmethod
    def getPolSpeed(self) -> float:
        pass

    @abstractmethod
    def setPolAccel(self, accel:float):
        '''
        accel: deg/sec^2
        '''
        pass

    @abstractmethod
    def setPolDecel(self, decel):
        '''
        decel: deg/sec^2
        '''
        pass

    @abstractmethod
    def getPolTorque(self) -> float:
        '''
        Voltage in range -9.9982 to +9.9982
        '''
        pass

    @abstractmethod
    def homeAxis(self, axis:str, timeout:float = None):
        pass

    @abstractmethod
    def setZeroAxis(self, axis:str):
        pass



    @abstractmethod
    def getMotorStatus(self) -> MotorStatus:
        pass
    
    @abstractmethod
    def getPosition(self) -> Position:
        pass

    @abstractmethod
    def positionInBounds(self, pos: Position) -> bool:
        pass

    @abstractmethod
    def estimateMoveTime(self, fromPos: Position, toPos: Position) -> float:
        '''
        estmate how many seconds it will take to move fromPos toPos.
        '''
        pass

    @abstractmethod
    def setNextPos(self, nextPos: Position):
        pass

    @abstractmethod
    def setTriggerInterval(self, interval_mm:float):
        '''
        interval_mm: mm
        '''
        pass

    @abstractmethod
    def startMove(self, withTrigger:bool, timeout:float = None):
        pass

    @abstractmethod
    def stopMove(self):
        pass

    @abstractmethod
    def getMoveStatus(self) -> MoveStatus:
        pass
