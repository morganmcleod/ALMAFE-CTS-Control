'''
Operate the Galil DMC 21x3 motor controller.
This code was ported from the existing LabVIEW code.
It uses a TCP/IP socket to communicate directly with the hardware.
'''

from .schemas import MotorStatus, MoveStatus, Position
from .MCInterface import MCInterface, MCError
from ..Common.RemoveDelims import removeDelims
import socket
import time
from math import sqrt, copysign
from typing import Union
import logging
import queue
import threading
from pydantic import BaseModel

class QueueItem(BaseModel):
    request: bytes
    response: bytes = b''
    replySize: int = 1
    complete: bool = False


class MotorController(MCInterface):
    SOCKET_TIMEOUT = 5    # sec
    STEPS_PER_DEGREE = 225
    STEPS_PER_MM = 5000
    X_MIN = 0
    Y_MIN = 0
    X_MAX = 400
    Y_MAX = 300
    POL_MIN = -200
    POL_MAX = 180
    DEFAULT_HOST = "169.254.1.1"
    DEFAULT_PORT = 2055
    DELIMS = b'[:,\s\r\n]'
    XY_SPEED = 10
    POL_SPEED = 20
    XY_ACCEL = 15
    POL_ACCEL = 10
    XY_DECEL = 15
    POL_DECEL = 10
    # constants from DMC-2103 Firmware Command Reference:
    MIN_XYSPEED_STEPS = 2           
    MAX_XYSPEED_STEPS = 12000000
    MIN_POLSPEED_STEPS = 2
    MAX_POLSPEED_STEPS = 3000000
    MIN_ACCEL_STEPS = 1024          # also decel
    MAX_ACCEL_STEPS = 67107840      # also decel
    MIN_POL_TORQUE = -9.9982        # volts analog output signal
    MAX_POL_TORQUE = 9.9982         # "

    def __init__(self, host = DEFAULT_HOST, port = DEFAULT_PORT):
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.logger.setLevel(logging.DEBUG)
        self.host = host
        self.port = port
        self.socket = None
        self.queue = queue.Queue()
        threading.Thread(target = self.queueWorker, daemon=True).start()
        self.reset()

    def __del__(self):
        try:
            self.socket.close()
        except:
            pass
        self.socket = None

    def __connectSocket(self):
        try:
            self.socket.close()
        except:
            pass
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.SOCKET_TIMEOUT)
        self.socket.connect((self.host, self.port))

    def __checkHandshake(self, context, expected, recv):
        if  recv != expected:
            self.logger.warning(f"{context}: expected:{expected}, recv:{recv}")
    
    def reset(self):
        self.start = False
        self.stop = False
        self.nextPos = Position(x=0, y=0, z=0)
        self.position = Position(x=0, y=0, z=0)
        self.motorStatus = MotorStatus()
        self.__connectSocket()
        self.xySpeed = self.getXYSpeed()
        self.polSpeed = self.getPolSpeed()
        self.__setVectorSpeed(self.xySpeed)
        # Stop command. All motors come to decelerated stop.
        hs = self.query(b'ST;')
        self.__checkHandshake("MotorController.reset", b':', hs)
        # The CF command directs the controller to send unsolicited responses to the serial port or ethernet.
        # An unsolicited message is data generated by the controller which is not in response to a command sent by the host.
        hs = self.query(b'XQ#CF;')
        self.__checkHandshake("MotorController.reset", b':', hs)
        # Execute the setup routine that should be previously saved to the motion controller card.        
        time.sleep(1.0)
        hs = self.query(b'XQ#SETUP;')
        self.__checkHandshake("MotorController.reset", b':', hs)
        

    def flush(self):
        flushed = b''
        prevTimeout = self.socket.gettimeout()
        self.socket.settimeout(0.001)
        while True:
            try:
                data = self.socket.recv(1)
                flushed += data
            except:
                self.socket.settimeout(prevTimeout)
                if flushed:
                    self.logger.debug(f"MotorController.flush:{flushed}")
                return

    def sendall(self, request: bytes) -> bool:

        try:
            self.socket.sendall(request)
            # self.logger.debug(f"MotorController.sendall:{request}")
            return True
        except socket.timeout:
            pass
            # self.logger.error("MotorController.sendall timeout")
        except Exception as e:
            self.logger.error(f"MotorController.sendall exception:{e}")
        return False

    def recv(self, replySize: int = 1) -> bytes:
        prevTimeout = self.socket.gettimeout()
        self.socket.settimeout(0.001)
        data = newData = b''
        endTime = time.time() + self.SOCKET_TIMEOUT
        while len(data) < replySize:
            try:
                newData = self.socket.recv(1)
                data += newData
            except:
                pass
            if not newData and time.time() > endTime:
                break
        # self.logger.debug(f"MotorController.recv:{data}")
        self.socket.settimeout(prevTimeout)
        return data

    def query(self, request: Union[bytes, str], replySize: int = 1) -> bytes:
        if isinstance(request, str):
            request = request.encode()
        
        qItem = QueueItem(request = request, replySize = replySize)
        self.queue.put(qItem)
                      
        timeout = time.time() + 2 * self.SOCKET_TIMEOUT
        while not qItem.complete:
            time.sleep(0.05)
            if time.time() > timeout:
                break

        return qItem.response

    def queueWorker(self):
        while True:
            item = self.queue.get()
            self.flush()
            if self.sendall(item.request):
                item.response = self.recv(item.replySize)
            item.complete = True

    def isConnected(self) -> bool:
        try:
            hs=self.query(b';')
            return hs == b':'
        except:
            return False

    def setXYSpeed(self, speed:float):
        '''
        speed: mm/second
        '''
        speedSteps = speed * self.STEPS_PER_MM
        assert(self.MIN_XYSPEED_STEPS < speed < self.MAX_XYSPEED_STEPS)
        self.xySpeed = speed
        hs = self.query(f"SP {speedSteps}, {speedSteps};")
        self.__checkHandshake("MotorController.setXYSpeed", b':', hs)
        self.__setVectorSpeed(speed)

    def __setVectorSpeed(self, speed:float):
        speedSteps = speed * self.STEPS_PER_MM
        hs = self.query(f"VS {speedSteps};")
        self.__checkHandshake("MotorController.__setVectorSpeed", b':', hs)

    def getXYSpeed(self) -> float:
        '''
        speed: mm/second
        '''
        # Send the variable format command to specifiy 10 digits before the 
        # decimal point and zero after.  Send the read speed command.
        data = self.query(b'\nLZ 0; VF 10,0; SP?;', replySize = 13)
        data = removeDelims(data, self.DELIMS)
        speed = int(data[0])
        assert(self.MIN_XYSPEED_STEPS < speed < self.MAX_XYSPEED_STEPS)
        speed = float(speed / self.STEPS_PER_MM)
        return speed

    def setXYAccel(self, accel:float):
        '''
        accel mm/sec^2
        '''
        accel *= self.STEPS_PER_MM
        assert(self.MIN_ACCEL_STEPS < accel < self.MAX_ACCEL_STEPS)
        hs = self.query(f"AC {accel}, {accel};")
        self.__checkHandshake("MotorController.setXYAccel", b':', hs)

    def getXYAccel(self) -> float:
        '''
        accel mm/sec^2
        '''
        data = self.query(b'\nLZ 0; VF 10,0; AC?;', replySize = 13)
        data = removeDelims(data, self.DELIMS)
        accel = int(data[0])
        assert(self.MIN_ACCEL_STEPS < accel < self.MAX_ACCEL_STEPS)
        accel = float(accel / self.STEPS_PER_MM)
        return accel

    def setXYDecel(self, decel:float):
        '''
        decel mm/sec^2
        '''
        decel *= self.STEPS_PER_MM
        assert(self.MIN_ACCEL_STEPS <= decel <= self.MAX_ACCEL_STEPS)
        hs = self.query(f"DC {decel}, {decel};")
        self.__checkHandshake("MotorController.setXYDecel", b':', hs)

    def getXYDecel(self) -> float:
        '''
        decel mm/sec^2
        '''
        data = self.query(b'\nLZ 0; VF 10,0; DC?;', replySize = 13)
        data = removeDelims(data, self.DELIMS)
        decel = int(data[0])
        assert(self.MIN_ACCEL_STEPS < decel < self.MAX_ACCEL_STEPS)
        decel = float(decel / self.STEPS_PER_MM)
        return decel

    def setPolSpeed(self, speed:float):
        '''
        speed: degrees/second
        '''
        self.polSpeed = speed
        speed *= self.STEPS_PER_DEGREE
        assert(self.MIN_POLSPEED_STEPS <= speed <= self.MAX_POLSPEED_STEPS)
        hs = self.query(str.encode(f"SPC={speed};"))
        self.__checkHandshake("MotorController.setPolSpeed", b':', hs)

    def getPolSpeed(self) -> float:
        '''
        speed: degrees/second
        '''
        data = self.query(b'\nLZ 0; VF 10,0; SP ?,?,?;', replySize = 31)
        data = removeDelims(data, self.DELIMS)
        speed = int(data[2])
        assert(self.MIN_POLSPEED_STEPS < speed < self.MAX_POLSPEED_STEPS)
        speed = float(speed / self.STEPS_PER_DEGREE)
        return speed

    def setPolAccel(self, accel:float):
        '''
        accel: deg/sec^2
        '''
        accel *= self.STEPS_PER_DEGREE
        assert(self.MIN_ACCEL_STEPS <= accel <= self.MAX_ACCEL_STEPS)
        hs = self.query(f"ACC={accel};")
        self.__checkHandshake("MotorController.setPolAccel", b':', hs)

    def getPolAccel(self) -> float:
        '''
        accel: deg/sec^2
        '''
        data = self.query(b'\nLZ 0; VF 10,0; AC ?,?,?;', replySize = 31)
        data = removeDelims(data, self.DELIMS)
        accel = int(data[2])
        assert(self.MIN_ACCEL_STEPS < accel < self.MAX_ACCEL_STEPS)
        accel = float(accel / self.STEPS_PER_DEGREE)
        return accel

    def setPolDecel(self, decel:float):
        '''
        decel: deg/sec^2
        '''
        decel *= self.STEPS_PER_DEGREE
        assert(1024 <= decel <= 67107840)
        hs = self.query(f"DCC={decel};")
        self.__checkHandshake("MotorController.setPolDecel", b':', hs)

    def getPolDecel(self) -> float:
        '''
        decel: deg/sec^2
        '''
        data = self.query(b'\nLZ 0; VF 10,0; DC ?,?,?;', replySize = 31)
        data = removeDelims(data, self.DELIMS)
        decel = int(data[2])
        assert(self.MIN_ACCEL_STEPS < decel < self.MAX_ACCEL_STEPS)
        decel = float(decel / self.STEPS_PER_DEGREE)
        return decel

    def getPolTorque(self) -> float:
        '''
        + or - percentage
        '''
        data = self.query(b'TTC;', replySize = 10)
        data = removeDelims(data, self.DELIMS)
        torque = float(data[0]) if data else 0
        assert(self.MIN_POL_TORQUE <= torque <= self.MAX_POL_TORQUE)
        torque = round(copysign(abs(torque) / self.MAX_POL_TORQUE, torque) * 100, 1)
        return torque

    def homeAxis(self, axis:str = 'xy', timeout:float = None):
        if self.getMotorStatus().inMotion():
            raise MCError("Cannot home axis while scanner is in motion.")
        
        axis = axis.lower()
        if axis == 'x':
            self.nextPos.x = 0
            hs = self.query(b'HMA; BGA;', replySize = 2)
            self.__checkHandshake("MotorController.homeAxis", b'::', hs)
        elif axis == 'y':
            self.nextPos.y = 0
            hs = self.query(b'HMB; BGB;', replySize = 2)
            self.__checkHandshake("MotorController.homeAxis", b'::', hs)
        elif axis == 'pol':
            self.nextPos.pol = 0
            hs = self.query(b'JGC=300; FIC; BGC;', replySize = 3)
            self.__checkHandshake("MotorController.homeAxis", b':::', hs)
        elif axis == 'xy':
            self.nextPos.x = 0
            self.nextPos.y = 0
            hs = self.query(b'HMAB; BGAB;', replySize = 2)
            self.__checkHandshake("MotorController.homeAxis", b'::', hs)
        else:
            raise ValueError(f"Unsupported option for axis: '{axis}'")

        self.start = True
        self.stop = False
        self.timeout = timeout
        self.startTime = time.time()

    def setZeroAxis(self, axis:str = 'xypol'):
        if self.getMotorStatus().inMotion():
            raise MCError("Cannot zero axis while scanner is in motion.")

        axis = axis.lower()
        if axis == 'x':
            cmd = b'DP 0;'
        elif axis == 'y':
            cmd = b'DP ,0;'
        elif axis == 'pol':
            cmd = b'DP ,,0;'
        elif axis == 'xy':
            cmd = b'DP 0,0;'
        elif axis == 'xypol;':
            cmd = b'DP 0,0,0'
        else:
            raise ValueError(f"Unsupported option for axis: '{axis}'")
        hs = self.query(cmd)
        self.__checkHandshake("MotorController.setZeroAxis", b':', hs)

    def servoHere(self):
        if self.getMotorStatus().inMotion():
            raise MCError("Cannot servo here while scanner is in motion.")
        hs = self.query(b'SH;')
        self.__checkHandshake("MotorController.servoHere", b':', hs)
        # Execute the setup routine that should be previously saved to the motion controller card.        
        time.sleep(1.0)
        hs = self.query(b'XQ#SETUP;')
        self.__checkHandshake("MotorController.reset", b':', hs)

    def getErrorCode(self) -> str:
        data = self.query(b'TC1;', replySize=100)
        return str(data)

    def getMotorStatus(self) -> MotorStatus:
        replySize = 22
        data = self.query(b'TS;', replySize)
        if not data or len(data) < replySize:
            return self.motorStatus
        data = removeDelims(data, self.DELIMS)
        if len(data) < 3:
            return self.motorStatus
        self.motorStatus = MotorStatus(
            xPower = bool(1 - (int(data[0]) >> 5) & 1),   # !bit 5
            yPower = bool(1 - (int(data[1]) >> 5) & 1),
            polPower = bool(1 - (int(data[2]) >> 5) & 1),
            xMotion = bool((int(data[0]) >> 7) & 1),      # bit 7
            yMotion = bool((int(data[1]) >> 7) & 1),
            polMotion = bool((int(data[2]) >> 7) & 1),
            polTorque = self.getPolTorque()
        )
        return self.motorStatus
    
    def getPosition(self) -> Position:
        # Send the position format command to specifiy 10 digits before the 
        # decimal point and zero after.  Send the read position command.
        # RP is necessary because TP doesn't work for stepper motors.
        replySize = 44
        data = self.query(b'\nLZ 0; PF 10,0; RPX; RPY; TPZ;', replySize)
        if not data or len(data) < replySize:
            return self.position
        data = removeDelims(data, self.DELIMS)
        # negate because motors are opposite what we want to call (0,0)
        self.position = Position(
            x = round(-(int(data[0]) / self.STEPS_PER_MM), 2),
            y = round(-(int(data[1]) / self.STEPS_PER_MM), 2),
            pol = round(int(data[2]) / self.STEPS_PER_DEGREE, 2)
        )
        return self.position

    def positionInBounds(self, pos: Position) -> bool:
        return (self.X_MIN <= pos.x <= self.X_MAX) and \
               (self.Y_MIN <= pos.y <= self.Y_MAX) and \
               (self.POL_MIN <= pos.pol <= self.POL_MAX)

    def estimateMoveTime(self, fromPos: Position, toPos: Position) -> float:
        '''
        Estmate how long it will take to move fromPos toPos.
        This is a significant over-estimate because we only want to time out if something is really wrong.
        '''
        vector = fromPos.calcMove(toPos)
        xyTime = sqrt(vector.x ** 2 + vector.y ** 2) / self.xySpeed
        polTime = abs(vector.pol) / self.polSpeed
        return max(xyTime, polTime) * 3 + 2.0

    def setNextPos(self, nextPos: Position):
        if nextPos.x < 0:
            nextPos.x = 0
        if nextPos.x > self.X_MAX:
            nextPos.x = self.X_MAX
        if nextPos.y < 0:
            nextPos.y = 0
        if nextPos.y > self.Y_MAX:
            nextPos.y = self.Y_MAX
        if nextPos.pol < self.POL_MIN:
            nextPos.pol = self.POL_MIN
        if nextPos.pol > self.POL_MAX:
            nextPos.pol = self.POL_MAX
        
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
        self.__checkHandshake("MotorController.setTriggerInterval", b':', hs)

    def startMove(self, withTrigger:bool = False, timeout:float = None):
        if self.getMotorStatus().inMotion():
            raise MCError("Cannot start move while scanner is already in motion.")
        
        # set our speeds.  They can get reset by some operations e.g. homing an axis.
        self.setXYSpeed(self.xySpeed)
        self.setPolSpeed(self.polSpeed)

        self.start = True
        self.stop = False
        self.timeout = timeout
        self.startTime = time.time()

        vector = self.getPosition().calcMove(self.nextPos)
        # position absolute the pol axis:
        hs = self.query(f"PAC={self.nextPos.pol * self.STEPS_PER_DEGREE};")
        self.__checkHandshake("MotorController.startMove", b':', hs)
        # position relative the X and Y axes:
        hs = self.query(f"PR {vector.x * self.STEPS_PER_MM}, {vector.y * self.STEPS_PER_MM};")
        self.__checkHandshake("MotorController.startMove", b':', hs)
        if withTrigger:
            hs = self.query(b'XQ #TRIGMV;')
        else:
            hs = self.query(b'BGABC;')
        self.__checkHandshake("MotorController.startMove", b':', hs)

    def stopMove(self):
        self.start = False
        self.stop = True
        hs = self.query(b'ST;')
        self.__checkHandshake("MotorController.stopMove", b':', hs)

    def getMoveStatus(self) -> MoveStatus:
        result = MoveStatus(
            stopSignal = self.stop,
            timedOut = ((time.time() - self.startTime) > self.timeout) if self.timeout else False
        )
        status = self.getMotorStatus()
        pos = self.getPosition()
        if (not status.inMotion() and pos == self.nextPos):
            result.success = True
        elif status.powerFail():
            result.powerFail = True
        return result

    def waitForMove(self, timeout: float = None) -> MoveStatus:
        startTime = time.time()
        elapsed = 0.0
        moveStatus = self.getMoveStatus()
        while not self.stop and not moveStatus.shouldStop():
            elapsed = time.time() - startTime
            if timeout and elapsed > timeout:
                break
            time.sleep(0.5)
            moveStatus = self.getMoveStatus()
            torque = self.getPolTorque()
            if abs(torque) > 20:
                self.logger.warning(f"waitForMove: pol torque:{torque} %")
        
        if moveStatus.isError():
            self.logger.error(moveStatus.getText())
        return moveStatus
