'''
Data models and interface for three-axis motor controller
'''
from abc import ABC, abstractmethod
from pydantic import BaseModel

class MotorStatus(BaseModel):
    xPower: bool
    yPower: bool
    polPower: bool
    xMotion: bool
    yMotion: bool
    polMotion: bool

    def powerFail(self) -> bool:
        return not (self.xPower and self.yPower and self.polPower)

    def inMotion(self) -> bool:
        return self.xMotion or self.yMotion or self.polMotion  

    def getText(self) -> str:
        return f"powerFail={self.powerFail()} inMotion={self.inMotion()}"

class MoveStatus(BaseModel):
    success: bool = False
    powerFail: bool = False
    timedOut: bool = False
    stopSignal: bool = False

    def isError(self) -> bool:
        return self.powerFail or self.timedOut

    def shouldStop(self) -> bool:
        return self.success or self.stopSignal or self.isError()

    def getText(self) -> str:
        return f"success={self.success}, powerFail={self.powerFail}, timedOut={self.timedOut}, stopSignal={self.stopSignal}"


class Position(BaseModel):
    x: float = 0
    y: float = 0
    pol: float = 0

    def __eq__(self, other) -> bool:
        return self.x == other.x and \
               self.y == other.y and \
               abs(self.pol - other.pol) < 0.1

    def calcMove(self, dest):
        return Position(x = self.x - dest.x,
                        y = self.y - dest.y,
                        pol = self.pol - dest.pol)

    def getText(self) -> str:
        return f"({self.x}, {self.y}, {self.pol})"

class MCInterface(ABC):

    @abstractmethod
    def setup(self):
        pass

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
    def setTriggerInterval(self, interval:float):
        '''
        interval: mm
        '''
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
    def startMove(self, withTrigger:bool, timeout:float = None):
        pass

    @abstractmethod
    def stopMove(self):
        pass

    @abstractmethod
    def getMoveStatus(self) -> MoveStatus:
        pass
