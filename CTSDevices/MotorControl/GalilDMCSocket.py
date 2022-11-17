'''
Operate the Galil DMC 21x3 motor controller.
This code was ported from the existing LabVIEW code.
It uses a TCP/IP socket to communicate directly with the hardware.
'''

import socket
import re
from time import time
from math import sqrt
from pydantic import BaseModel

class GMotorStatus(BaseModel):
    xPower: bool
    yPower: bool
    zPower: bool
    xMotion: bool
    yMotion: bool
    zMotion: bool

    def powerFail(self):
        return not (self.xPower and self.yPower and self.zPower)

    def inMotion(self):
        return self.xMotion or self.yMotion or self.zMotion  
 
class GPosition(BaseModel):
    x: float = 0
    y: float = 0
    z: float = 0

    def __eq__(self, other):
        return self.x == other.x and \
               self.y == other.y and \
               abs(self.z - other.z) < 0.1

    def calcMove(self, dest):
        return GPosition(x = self.x - dest.x,
                        y = self.y - dest.y,
                        z = self.z - dest.z)

class MotorController():
    STEPS_PER_DEGREE = 225
    STEPS_PER_MM = 5000
    X_MIN = 0
    Y_MIN = 0
    X_MAX = 400
    Y_MAX = 300
    HOST = "169.254.1.1"
    PORT = 2055
    DELIMS = b'[:,\s\r\n]'

    def __init__(self):
        self.reset()

    def reset(self):
        self.stop = False
        self.nextPos = GPosition(x=0, y=0, z=0)
        self.speedXY = self.getSpeedXY()
        self.speedZ = self.getSpeedZ()
        
    def query(self, request: bytes, replySize: int) -> bytes:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.HOST, self.PORT))
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

    def isConnected(self):
        hs=self.query(b';', 1)
        return hs == b':'

    def setSpeedXY(self, speed: int = 10):
        '''
        speed: mm/second
        '''
        self.speedXY = speed
        speed *= self.STEPS_PER_MM
        hs = self.query(str.encode(f"SP {speed}, {speed};"), 1)
        assert(hs == b':')

    def getSpeedXY(self):
        # Send the variable format command to specifiy 10 digits before the 
        # decimal point and zero after.  Send the read speed command.
        data = self.query(b'\nLZ 0; VF 10,0; VS?;', 13)
        data = self.removeDelims(data)
        speed = int(data[0]) / self.STEPS_PER_MM
        assert(2 < speed < 3000000)
        return speed

    def setAccelXY(self, accel):
        '''
        accel mm/sec^2
        '''
        accel *= self.STEPS_PER_MM
        assert(1024 <= accel <= 68431360)
        hs = self.query(str.encode(f"AC {accel}, {accel};"), 1)
        assert(hs == b':')

    def setDecelXY(self, decel):
        '''
        decel mm/sec^2
        '''
        decel *= self.STEPS_PER_MM
        assert(1024 <= decel <= 68431360)
        hs = self.query(str.encode(f"DC {decel}, {decel};"), 1)
        assert(hs == b':')

    def setSpeedZ(self, speed:int = 20):
        '''
        speed: degrees/second
        '''
        self.speedZ = speed
        speed *= self.STEPS_PER_DEGREE
        hs = self.query(str.encode(f"SPC={speed};"), 1)
        assert(hs == b':')

    def getSpeedZ(self):
        # Send the variable format command to specifiy 10 digits before the 
        # decimal point and zero after.  Send the read speed command.
        data = self.query(b'\nLZ 0; VF 10,0; SP ?,?,?;', 31)
        data = self.removeDelims(data)
        speed = int(data[2]) / self.STEPS_PER_DEGREE
        assert(1 < speed < 12000000)
        return speed

    def setAccelZ(self, accel):
        '''
        accel: deg/sec^2
        '''
        accel *= self.STEPS_PER_DEGREE
        assert(1024 <= accel <= 67107840)
        hs = self.query(str.encode(f"ACC={accel};"), 1)
        assert(hs == b':')

    def setDecelZ(self, decel):
        '''
        decel: deg/sec^2
        '''
        decel *= self.STEPS_PER_DEGREE
        assert(1024 <= decel <= 67107840)
        hs = self.query(str.encode(f"DCC={decel};"), 1)
        assert(hs == b':')

    def getTorqueZ(self):
        data = self.query(b'TTZ;', 9)
        data = self.removeDelims(data)
        return float(data(0))

    def homeAxis(self, axis='xy'):
        axis = axis.lower()
        if axis == 'x':
            self.nextPos.x = 0
            hs = self.query(b'HMA; BGA;', 2)
            assert(hs == b'::')
        elif axis == 'y':
            self.nextPos.y = 0
            hs = self.query(b'HMB; BGB;', 2)
            assert(hs == b'::')
        elif axis == 'z':
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

    def setAxisZero(self, axis='xyz'):
        axis = axis.lower()
        if axis == 'x':
            cmd = b'DP 0'
        elif axis == 'y':
            cmd = b'DP ,0'
        elif axis == 'z':
            cmd = b'DP ,,0'
        elif axis == 'xy':
            cmd = b'DP 0,0'
        elif axis == 'xyz':
            cmd = b'DP 0,0,0'
        else:
            raise ValueError(f"Unsupported option for axis: '{axis}'")
        hs = self.query(cmd, 1)
        assert(hs == b':')

    def setTriggerInterval(self, interval):
        '''
        interval: mm
        '''
        # Set the DISTANCE variable used in the #TRIGMV routine
        interval *= self.STEPS_PER_DEGREE
        hs = self.query(str.encode(f"DISTANCE={interval};"), 1)
        assert(hs == b':')

    def getGMotorStatus(self):
        data = self.query(b'TS;', 18)
        data = self.removeDelims(data)
        return GMotorStatus(
            xPower = bool(1 - (int(data[0]) >> 4) & 1), # ~ bit 5
            yPower = bool(1 - (int(data[1]) >> 4) & 1),
            zPower = bool(1 - (int(data[2]) >> 4) & 1),
            xMotion = bool((int(data[0]) >> 6) & 1),      # bit 7
            yMotion = bool((int(data[1]) >> 6) & 1),
            zMotion = bool((int(data[2]) >> 6) & 1)
        )
    
    def getGPosition(self):
        # Send the position format command to specifiy 10 digits before the 
        # decimal point and zero after.  Send the read position command.
        # RP is necessary because TP doesn't work for stepper motors.
        data = self.query(b'\nLZ 0; PF 10,0; RPX; RPY; TPZ;', 51)
        data = self.removeDelims(data)
        # negate because motors are opposite what we want to call (0,0)
        return GPosition(
            x = -(int(data[0]) / self.STEPS_PER_MM),
            y = -(int(data[1]) / self.STEPS_PER_MM),
            z = int(data[2]) / self.STEPS_PER_DEGREE
        )

    def positionInBounds(self, pos: GPosition):
        return (self.X_MIN <= pos.x <= self.X_MAX) and (self.Y_MIN <= pos.y <= self.Y_MAX)

    def estimateMoveTime(self, fromPos: GPosition, toPos: GPosition):
        '''
        estmate how long it will take to move fromPos toPos.
        Add 25% to account for accel and decel.
        '''
        vector = fromPos.calcMove(toPos)
        timeXY = sqrt(vector.x ** 2 + vector.y ** 2) / self.speedXY
        timeZ = abs(vector.z) / self.speedZ
        return max(timeXY, timeZ) * 1.25

    def SetNextPos(self, nextPos: GPosition):
        self.nextPos = nextPos
    
    def startMove(self, withTrigger: bool):
        self.stop = False
        vector = self.getGPosition().calcMove(self.nextPos)
        # position absolute the Z axis:
        hs = self.query(str.encode(f"PAC={self.nextPos.z * self.STEPS_PER_DEGREE};"), 1)
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
        self.stop = True
        hs = self.query(b'ST;', 1)
        assert(hs == b':')

    def waitForGPosition(self, timeout):
        startTime = time()
        success = False
        powerFail = False
        timedOut = False
        while not success and not powerFail and not timedOut and not self.stop:
            timedOut = (time() - startTime > timeout)
            status = self.getGMotorStatus()
            pos = self.getGPosition()
            if (not status.inMotion() and pos == self.nextPos):
                success = True
            elif status.powerFail():
                powerFail = True
        return {
            'success': success,
            'powerFail' : powerFail,
            'timedOut': timedOut,
            'stopSignal': self.stop
        }
