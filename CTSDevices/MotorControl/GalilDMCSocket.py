'''
Operate the Galil DMC 21x3 motor controller.
This code was ported from the existing LabVIEW code.
It uses a TCP/IP socket to communicate directly with the hardware.
'''

from .MCInterface import MCInterface, MotorStatus, MoveStatus, Position
import socket
import re
from time import time
from math import sqrt

class MotorController(MCInterface):
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
        self.reset()
        self.host = host
        self.port = port

    def reset(self):
        self.start = False
        self.stop = False
        self.nextPos = Position(x=0, y=0, z=0)
        self.xySpeed = self.getSpeedXY()
        self.polSpeed = self.getSpeedZ()
        
    def query(self, request: bytes, replySize: int) -> bytes:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            sent = s.send(request)
            if not sent:
                raise RuntimeError("socket connection broken")
            else:
                data = s.recv(replySize)
                if data == b'':
                    raise RuntimeError("socket connection broken")
                return data

    def removeDelims(self, bData: bytes, bDelimsRe: bytes = DELIMS):
        d = re.split(bDelimsRe, bData)
        return [x for x in d if x]

    def setup(self):
        # send command to execute the Clear Faults, Motor Power ON, and
        # Setup routines that should be saved on the motion controller card.
        hs = self.query(b'ST;', 1)
        assert(hs == b':')
        hs = self.query(b'XQ#CF;', 1)
        assert(hs == b':')
        hs = self.query(b'XQ#SETUP;', 1)
        # assert(hs == b':')

    def isConnected(self) -> bool:
        hs=self.query(b';', 1)
        return hs == b':'

    def setXYSpeed(self, speed:float = XY_SPEED):
        '''
        speed: mm/second
        '''
        self.xySpeed = speed
        speed *= self.STEPS_PER_MM
        hs = self.query(str.encode(f"SP {speed}, {speed};"), 1)
        assert(hs == b':')

    def getXYSpeed(self) -> float:
        # Send the variable format command to specifiy 10 digits before the 
        # decimal point and zero after.  Send the read speed command.
        data = self.query(b'\nLZ 0; VF 10,0; VS?;', 13)
        data = self.removeDelims(data)
        speed = float(int(data[0]) / self.STEPS_PER_MM)
        assert(2 < speed < 3000000)
        return speed

    def setXYAccel(self, accel:float = XY_ACCEL):
        '''
        accel mm/sec^2
        '''
        accel *= self.STEPS_PER_MM
        assert(1024 <= accel <= 68431360)
        hs = self.query(str.encode(f"AC {accel}, {accel};"), 1)
        assert(hs == b':')

    def setXYDecel(self, decel:float = XY_DECEL):
        '''
        decel mm/sec^2
        '''
        decel *= self.STEPS_PER_MM
        assert(1024 <= decel <= 68431360)
        hs = self.query(str.encode(f"DC {decel}, {decel};"), 1)
        assert(hs == b':')

    def setPolSpeed(self, speed:float = POL_SPEED):
        '''
        speed: degrees/second
        '''
        self.polSpeed = speed
        speed *= self.STEPS_PER_DEGREE
        hs = self.query(str.encode(f"SPC={speed};"), 1)
        assert(hs == b':')

    def getPolSpeed(self) -> float:
        # Send the variable format command to specifiy 10 digits before the 
        # decimal point and zero after.  Send the read speed command.
        data = self.query(b'\nLZ 0; VF 10,0; SP ?,?,?;', 31)
        data = self.removeDelims(data)
        speed = float(int(data[2]) / self.STEPS_PER_DEGREE)
        assert(1 < speed < 12000000)
        return speed

    def setPolAccel(self, accel:float = POL_ACCEL):
        '''
        accel: deg/sec^2
        '''
        accel *= self.STEPS_PER_DEGREE
        assert(1024 <= accel <= 67107840)
        hs = self.query(str.encode(f"ACC={accel};"), 1)
        assert(hs == b':')

    def setPolDecel(self, decel:float = POL_DECEL):
        '''
        decel: deg/sec^2
        '''
        decel *= self.STEPS_PER_DEGREE
        assert(1024 <= decel <= 67107840)
        hs = self.query(str.encode(f"DCC={decel};"), 1)
        assert(hs == b':')

    def getPolTorque(self) -> float:
        '''
        Voltage in range -9.9982 to +9.9982
        '''
        data = self.query(b'TTZ;', 9)
        data = self.removeDelims(data)
        return float(data(0))

    def homeAxis(self, axis:str = 'xy', timeout:float = None):
        if self.getMotorStatus().inMotion():
            raise RuntimeError("Cannot home axis while scanner is in motion.")
        
        axis = axis.lower()
        if axis == 'x':
            self.nextPos.x = 0
            hs = self.query(b'HMA; BGA;', 2)
            assert(hs == b'::')
        elif axis == 'y':
            self.nextPos.y = 0
            hs = self.query(b'HMB; BGB;', 2)
            assert(hs == b'::')
        elif axis == 'pol':
            self.nextPos.z = 0
            hs = self.query(b'JGC=300; FIC; BGC;', 3)
            assert(hs == b':::')
        elif axis == 'xy':
            self.nextPos.x = 0
            self.nextPos.y = 0
            hs = self.query(b'HMAB; BGAB;', 2)
            assert(hs == b'::')
        else:
            raise ValueError(f"Unsupported option for axis: '{axis}'")

        self.start = True
        self.stop = False
        self.timeout = timeout
        self.startTime = time()

    def setZeroAxis(self, axis:str = 'xypol'):
        if self.getMotorStatus().inMotion():
            raise RuntimeError("Cannot zero axis while scanner is in motion.")

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
        hs = self.query(cmd, 1)
        assert(hs == b':')

    def setTriggerInterval(self, interval:float):
        '''
        interval: mm
        '''
        # Set the DISTANCE variable used in the #TRIGMV routine
        interval = int(interval * self.STEPS_PER_MM)
        hs = self.query(str.encode(f"DISTANCE={interval};"), 1)
        assert(hs == b':')

    def getMotorStatus(self) -> MotorStatus:
        data = self.query(b'TS;', 18)
        data = self.removeDelims(data)
        return MotorStatus(
            xPower = bool(1 - (int(data[0]) >> 4) & 1), # ~ bit 5
            yPower = bool(1 - (int(data[1]) >> 4) & 1),
            polPower = bool(1 - (int(data[2]) >> 4) & 1),
            xMotion = bool((int(data[0]) >> 6) & 1),      # bit 7
            yMotion = bool((int(data[1]) >> 6) & 1),
            polMotion = bool((int(data[2]) >> 6) & 1)
        )
    
    def getPosition(self) -> Position:
        # Send the position format command to specifiy 10 digits before the 
        # decimal point and zero after.  Send the read position command.
        # RP is necessary because TP doesn't work for stepper motors.
        data = self.query(b'\nLZ 0; PF 10,0; RPX; RPY; TPZ;', 51)
        data = self.removeDelims(data)
        # negate because motors are opposite what we want to call (0,0)
        return Position(
            x = -(int(data[0]) / self.STEPS_PER_MM),
            y = -(int(data[1]) / self.STEPS_PER_MM),
            pol = int(data[2]) / self.STEPS_PER_DEGREE
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
        polTime = abs(vector.pol) / self.polSpeed
        return max(xyTime, polTime) * 1.25

    def setNextPos(self, nextPos: Position):
        if self.positionInBounds(nextPos):
            self.nextPos = nextPos
        else:
            raise ValueError(f"SetNextPos out of bounds: {nextPos.getText()}")

    def startMove(self, withTrigger:bool, timeout:float = None):
        if self.getMotorStatus().inMotion():
            raise RuntimeError("Cannot start move while scanner is already in motion.")
        
        self.start = True
        self.stop = False
        self.timeout = timeout
        self.startTime = time()

        vector = self.getPosition().calcMove(self.nextPos)
        # position absolute the pol axis:
        hs = self.query(str.encode(f"PAC={self.nextPos.pol * self.STEPS_PER_DEGREE};"), 1)
        assert(hs == b':')
        # position relative the X and Y axes:
        hs = self.query(str.encode(f"PR {vector.x * self.STEPS_PER_MM}, {vector.y * self.STEPS_PER_MM};"), 1)
        assert(hs == b':')
        if withTrigger:
            hs = self.query(b'XQ #TRIGMV;', 1)
        else:
            hs = self.query(b'BGABC;', 1)
        assert(hs == b':')

    def stopMove(self):
        self.start = False
        self.stop = True
        hs = self.query(b'ST;', 1)
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
