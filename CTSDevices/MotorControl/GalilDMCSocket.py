'''
Operate the Galil DMC 21x3 motor controller.
This code was ported from the existing LabVIEW code.
It uses a TCP/IP socket to communicate directly with the hardware.
'''

from .schemas import MotorStatus, MoveStatus, Position
from .MCInterface import MCInterface, MCError
from ..Common.RemoveDelims import removeDelims
import socket
import re
from time import time
from math import sqrt
from typing import Union

class MotorController(MCInterface):
    SOCKET_TIMEOUT = 10    # sec
    STEPS_PER_DEGREE = 225
    STEPS_PER_MM = 5000
    X_MIN = 0
    Y_MIN = 0
    POL_MIN = 0
    X_MAX = 400
    Y_MAX = 300
    POL_MAX = 360
    DEFAULT_HOST = "169.254.1.1"
    DEFAULT_PORT = 2055
    DELIMS = b'[:,\s\r\n]'
    XY_SPEED = 10
    POL_SPEED = 20
    XY_ACCEL = 15
    POL_ACCEL = 10
    XY_DECEL = 15
    POL_DECEL = 10

    def __init__(self, host = DEFAULT_HOST, port = DEFAULT_PORT):
        self.host = host
        self.port = port
        self.reset()

    def reset(self):
        self.start = False
        self.stop = False
        self.nextPos = Position(x=0, y=0, z=0)
        self.xySpeed = self.getXYSpeed()
        self.polSpeed = self.getPolSpeed()
        
    def query(self, request: Union[bytes, str], replySize: int = 1) -> bytes:
        if isinstance(request, str):
            request = request.encode()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(self.SOCKET_TIMEOUT)
            s.connect((self.host, self.port))
            sent = s.send(request)
            if not sent:
                raise MCError("socket connection broken")
            else:
                data = None
                iter = 0
                while not data and iter < 3:
                    try:
                        data = s.recv(replySize)
                    except socket.timeout:
                        iter += 1
                if not data:
                    raise MCError("socket connection broken")
                if data == b'':
                    raise MCError("socket connection broken")
                return data

    def setup(self):
        # send command to execute the Clear Faults, Motor Power ON, and
        # Setup routines that should be saved on the motion controller card.
        hs = self.query(b'ST;')
        assert(hs == b':')
        hs = self.query(b'XQ#CF;')
        assert(hs == b':')
        hs = self.query(b'XQ#SETUP;')
        # assert(hs == b':')

    def isConnected(self) -> bool:
        try:
            hs=self.query(b';')
            return hs == b':'
        except:
            return False

    def setXYSpeed(self, speed:float = XY_SPEED):
        '''
        speed: mm/second
        '''
        self.xySpeed = speed
        speed *= self.STEPS_PER_MM
        hs = self.query(f"SP {speed}, {speed};")
        assert(hs == b':')

    def getXYSpeed(self) -> float:
        # Send the variable format command to specifiy 10 digits before the 
        # decimal point and zero after.  Send the read speed command.
        data = self.query(b'\nLZ 0; VF 10,0; VS?;', replySize = 13)
        data = removeDelims(data, self.DELIMS)
        speed = float(int(data[0]) / self.STEPS_PER_MM)
        assert(2 < speed < 3000000)
        return speed

    def setXYAccel(self, accel:float = XY_ACCEL):
        '''
        accel mm/sec^2
        '''
        accel *= self.STEPS_PER_MM
        assert(1024 <= accel <= 68431360)
        hs = self.query(f"AC {accel}, {accel};")
        assert(hs == b':')

    def setXYDecel(self, decel:float = XY_DECEL):
        '''
        decel mm/sec^2
        '''
        decel *= self.STEPS_PER_MM
        assert(1024 <= decel <= 68431360)
        hs = self.query(f"DC {decel}, {decel};")
        assert(hs == b':')

    def setPolSpeed(self, speed:float = POL_SPEED):
        '''
        speed: degrees/second
        '''
        self.polSpeed = speed
        speed *= self.STEPS_PER_DEGREE
        hs = self.query(str.encode(f"SPC={speed};"))
        assert(hs == b':')

    def getPolSpeed(self) -> float:
        # Send the variable format command to specifiy 10 digits before the 
        # decimal point and zero after.  Send the read speed command.
        data = self.query(b'\nLZ 0; VF 10,0; SP ?,?,?;', replySize = 31)
        data = removeDelims(data, self.DELIMS)
        speed = float(int(data[2]) / self.STEPS_PER_DEGREE)
        assert(1 < speed < 12000000)
        return speed

    def setPolAccel(self, accel:float = POL_ACCEL):
        '''
        accel: deg/sec^2
        '''
        accel *= self.STEPS_PER_DEGREE
        assert(1024 <= accel <= 67107840)
        hs = self.query(f"ACC={accel};")
        assert(hs == b':')

    def setPolDecel(self, decel:float = POL_DECEL):
        '''
        decel: deg/sec^2
        '''
        decel *= self.STEPS_PER_DEGREE
        assert(1024 <= decel <= 67107840)
        hs = self.query(f"DCC={decel};")
        assert(hs == b':')

    def getPolTorque(self) -> float:
        '''
        Voltage in range -9.9982 to +9.9982
        '''
        data = self.query(b'TTZ;', replySize = 9)
        data = removeDelims(data, self.DELIMS)
        return float(data(0))

    def homeAxis(self, axis:str = 'xy', timeout:float = None):
        if self.getMotorStatus().inMotion():
            raise MCError("Cannot home axis while scanner is in motion.")
        
        axis = axis.lower()
        if axis == 'x':
            self.nextPos.x = 0
            hs = self.query(b'HMA; BGA;', replySize = 2)
            assert(hs == b'::')
        elif axis == 'y':
            self.nextPos.y = 0
            hs = self.query(b'HMB; BGB;', replySize = 2)
            assert(hs == b'::')
        elif axis == 'pol':
            self.nextPos.pol = 0
            hs = self.query(b'JGC=300; FIC; BGC;', replySize = 3)
            assert(hs == b':::')
        elif axis == 'xy':
            self.nextPos.x = 0
            self.nextPos.y = 0
            hs = self.query(b'HMAB; BGAB;', replySize = 2)
            assert(hs == b'::')
        else:
            raise ValueError(f"Unsupported option for axis: '{axis}'")

        self.start = True
        self.stop = False
        self.timeout = timeout
        self.startTime = time()

    def setZeroAxis(self, axis:str = 'xypol'):
        if self.getMotorStatus().inMotion():
            raise MCError("Cannot zero axis while scanner is in motion.")

        axis = axis.lower()
        if axis == 'x':
            cmd = b'DP 0'
        elif axis == 'y':
            cmd = b'DP ,0'
        elif axis == 'pol':
            cmd = b'DP ,,0'
        elif axis == 'xy':
            cmd = b'DP 0,0'
        elif axis == 'xypol':
            cmd = b'DP 0,0,0'
        else:
            raise ValueError(f"Unsupported option for axis: '{axis}'")
        hs = self.query(cmd)
        assert(hs == b':')

    def getMotorStatus(self) -> MotorStatus:
        data = self.query(b'TS;', replySize = 19)
        data = removeDelims(data, self.DELIMS)
        return MotorStatus(
            xPower = bool(1 - (int(data[0]) >> 5) & 1),   # !bit 5
            yPower = bool(1 - (int(data[1]) >> 5) & 1),
            polPower = bool(1 - (int(data[2]) >> 5) & 1),
            xMotion = bool((int(data[0]) >> 7) & 1),      # bit 7
            yMotion = bool((int(data[1]) >> 7) & 1),
            polMotion = bool((int(data[2]) >> 7) & 1)
        )
    
    def getPosition(self) -> Position:
        # Send the position format command to specifiy 10 digits before the 
        # decimal point and zero after.  Send the read position command.
        # RP is necessary because TP doesn't work for stepper motors.
        data = self.query(b'\nLZ 0; PF 10,0; RPX; RPY; TPZ;', replySize = 51)
        data = removeDelims(data, self.DELIMS)
        # negate because motors are opposite what we want to call (0,0)
        return Position(
            x = round(-(int(data[0]) / self.STEPS_PER_MM), 1),
            y = round(-(int(data[1]) / self.STEPS_PER_MM), 1),
            pol = round(int(data[2]) / self.STEPS_PER_DEGREE, 1)
        )

    def positionInBounds(self, pos: Position) -> bool:
        return (self.X_MIN <= pos.x <= self.X_MAX) and \
               (self.Y_MIN <= pos.y <= self.Y_MAX) and \
               (self.POL_MIN <= pos.pol <= self.POL_MAX)

    def estimateMoveTime(self, fromPos: Position, toPos: Position) -> float:
        '''
        estmate how long it will take to move fromPos toPos.
        Add 25% to account for accel and decel.
        '''
        vector = fromPos.calcMove(toPos)
        xyTime = sqrt(vector.x ** 2 + vector.y ** 2) / self.xySpeed
        polTime = abs(vector.pol) / self.polSpeed + 1.0
        return max(xyTime, polTime) * 1.5

    def setNextPos(self, nextPos: Position):
        if not self.positionInBounds(nextPos):
            raise ValueError(f"SetNextPos out of bounds: {nextPos.getText()}")
        if self.getMotorStatus().inMotion():
            raise MCError("Cannot SetNextPos while scanner is already in motion.")
        else:
            self.nextPos = nextPos

    def setTriggerInterval(self, interval_mm:float):
        '''
        interval_mm: mm
        '''
        hs = self.query(f"DISTANCE={int(interval_mm * self.STEPS_PER_MM)};")
        assert(hs == b':')

    def startMove(self, withTrigger:bool, timeout:float = None):
        if self.getMotorStatus().inMotion():
            raise MCError("Cannot start move while scanner is already in motion.")
        
        self.start = True
        self.stop = False
        self.timeout = timeout
        self.startTime = time()

        vector = self.getPosition().calcMove(self.nextPos)
        # position absolute the pol axis:
        hs = self.query(f"PAC={self.nextPos.pol * self.STEPS_PER_DEGREE};")
        assert(hs == b':')
        # position relative the X and Y axes:
        hs = self.query(f"PR {vector.x * self.STEPS_PER_MM}, {vector.y * self.STEPS_PER_MM};")
        assert(hs == b':')
        if withTrigger:
            hs = self.query(b'XQ #TRIGMV;')
        else:
            hs = self.query(b'BGABC;')
        assert(hs == b':')

    def stopMove(self):
        self.start = False
        self.stop = True
        hs = self.query(b'ST;')
        assert(hs == b':')

    def getMoveStatus(self) -> MoveStatus:
        result = MoveStatus(
            stopSignal = self.stop,
            timedOut = ((time() - self.startTime) > self.timeout) if self.timeout else False
        )
        status = self.getMotorStatus()
        pos = self.getPosition()
        if (not status.inMotion() and pos == self.nextPos):
            result.success = True
        elif status.powerFail():
            result.powerFail = True
        return result
