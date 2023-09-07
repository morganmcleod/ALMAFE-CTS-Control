from .schemas import MotorStatus, MoveStatus, Position
from .MCInterface import MCInterface, MCError
from random import random
import time
from math import sqrt
from copy import deepcopy
import logging

class MCSimulator(MCInterface):
    X_MIN = 0
    Y_MIN = 0
    X_MAX = 400
    Y_MAX = 300
    POL_MIN = -200
    POL_MAX = 180
    XY_SPEED = 20
    POL_SPEED = 10
    X_INIT = 145
    Y_INIT = 145
    POL_INIT = -100
    
    def __init__(self):
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.start = False
        self.stop = False
        self.xySpeed = self.XY_SPEED
        self.polSpeed = self.POL_SPEED
        self.pos = Position(
            x = self.X_INIT,
            y = self.Y_INIT,
            pol = self.POL_INIT
        )
        self.nextPos = deepcopy(self.pos)
    
    def isConnected(self) -> bool:
        return True
    
    def setXYSpeed(self, speed:float = XY_SPEED):
        '''
        speed: mm/second
        '''
        self.xySpeed = speed
            
    def getXYSpeed(self) -> float:
        return self.xySpeed
    
    def setXYAccel(self, accel:float):
        '''
        accel mm/sec^2
        '''
        pass
    
    def setXYDecel(self, decel:float):
        '''
        decel mm/sec^2
        '''
        pass    
    
    def setPolSpeed(self, speed:float = POL_SPEED):
        '''
        speed: degrees/second
        '''
        self.polSpeed = speed
    
    def getPolSpeed(self) -> float:
        return self.polSpeed
    
    def setPolAccel(self, accel:float):
        '''
        accel: deg/sec^2
        '''
        pass
    
    def setPolDecel(self, decel:float):
        '''
        decel: deg/sec^2
        '''
        pass
    
    def getPolTorque(self) -> float:
        '''
        + or - percentage
        '''
        return 0.99
    
    def homeAxis(self, axis:str, timeout:float = None):
        if self.getMotorStatus().inMotion():
            raise MCError("Cannot home axis while scanner is in motion.")
        
        axis = axis.lower()
        if axis == 'x':
            self.nextPos.x = 0
            self.startMove(False, timeout)
        elif axis == 'y':
            self.nextPos.y = 0
            self.startMove(False, timeout)
        elif axis == 'pol':
            self.nextPos.pol = 0
            self.startMove(False, timeout)
        elif axis == 'xy':
            self.nextPos.x = 0
            self.nextPos.y = 0
            self.startMove(False, timeout)
        else:
            raise ValueError(f"Unsupported option for axis: '{axis}'")
    
    def setZeroAxis(self, axis:str):
        if self.getMotorStatus().inMotion():
            raise MCError("Cannot zero axis while scanner is in motion.")

        pos = self.getPosition()
        axis = axis.lower()
        if axis == 'x':
            pos.x = 0
        elif axis == 'y':
            pos.y = 0
        elif axis == 'pol':
            pos.pol = 0
        elif axis == 'xy':
            pos.x = 0
            pos.y = 0
        else:
            raise ValueError(f"Unsupported option for axis: '{axis}'")

        self.pos = pos
    
    def getMotorStatus(self) -> MotorStatus:
        pos = self.getPosition()
        return MotorStatus(
            xPower = True,
            yPower = True,
            polPower = True,
            xMotion = self.start and pos.x != self.nextPos.x,
            yMotion = self.start and pos.y != self.nextPos.y,
            polMotion = self.start and pos.pol != self.nextPos.pol
        )
    
    def getPosition(self) -> Position:
        if not self.start:
            return self.pos
        else:
            elapsed = time.time() - self.startTime
            if elapsed >= self.moveTime:
                self.pos = deepcopy(self.nextPos)
                self.start = False
                self.stop = False
                return self.pos
            else:
                portion = elapsed / self.moveTime
                vector = self.nextPos.calcMove(self.pos)
                return Position(
                    x = round(self.pos.x + vector.x * portion, 1),
                    y = round(self.pos.y + vector.y * portion, 1),
                    pol = round(self.pos.pol + vector.pol * portion, 1)
                )

    def positionInBounds(self, pos: Position) -> bool:
        return (self.X_MIN <= pos.x <= self.X_MAX) and \
               (self.Y_MIN <= pos.y <= self.Y_MAX) and \
               (self.POL_MIN <= pos.pol <= self.POL_MAX)
    
    def estimateMoveTime(self, fromPos: Position, toPos: Position) -> float:
        '''
        estmate how many seconds it will take to move fromPos toPos.
        '''
        vector = fromPos.calcMove(toPos)
        xyTime = sqrt(vector.x ** 2 + vector.y ** 2) / self.xySpeed
        polTime = abs(vector.pol) / self.polSpeed
        return max(xyTime, polTime) * 3.0 + 2
    
    def setNextPos(self, nextPos: Position):
        if not self.positionInBounds(nextPos):
            raise ValueError(f"SetNextPos out of bounds: {nextPos.getText()}")
        if self.getMotorStatus().inMotion():
            raise MCError("Cannot SetNextPos while scanner is already in motion.")
        else:
            self.nextPos = nextPos
    
    def setTriggerInterval(self, interval_mm:float):
        '''
        interval: mm
        '''
        self.triggerInterval = interval_mm

    def startMove(self, withTrigger:bool, timeout:float = None):
        if self.getMotorStatus().inMotion():
            raise MCError("Cannot start move while scanner is already in motion.")
        
        self.timeout = timeout
        self.startTime = time.time()
        # for simulation, this movetime is used in getPosition so it must be smaller than the estimate:
        # simulation has infitnite accel/decel!
        self.moveTime = self.estimateMoveTime(self.pos, self.nextPos) * 0.9
        self.start = True
        self.stop = False
    
    def stopMove(self):
        # if mid-move save where we were stopped:
        stoppedAt = self.getPosition() if self.start else self.pos
        self.start = False
        self.stop = True
        self.pos = stoppedAt
    
    def getMoveStatus(self) -> MoveStatus:
        timedOut = ((time.time() - self.startTime) > self.timeout) if self.timeout else False
        result = MoveStatus(
            stopSignal = self.stop,
            timedOut = timedOut
        )
        status = self.getMotorStatus()
        pos = self.getPosition()
        # self.logger.debug(f"{status.getText()} {pos.getText()}")
        if (not timedOut and not status.inMotion() and pos == self.nextPos):
            result.success = True
        elif status.powerFail():
            result.powerFail = True
        return result

    def waitForMove(self, timeout: float = None) -> MoveStatus:
        startTime = time.time()
        elapsed = 0.0
        moveStatus = self.getMoveStatus()
        if timeout:
            self.timeout = timeout
        while not self.stop and not moveStatus.shouldStop():
            elapsed = time.time() - startTime
            if self.timeout and elapsed > self.timeout:
                break
            time.sleep(0.5)
            moveStatus = self.getMoveStatus()
            torque = self.getPolTorque()
            if abs(torque) > 20:
                self.logger.warning(f"waitForMove: pol torque:{torque} %")

        return moveStatus