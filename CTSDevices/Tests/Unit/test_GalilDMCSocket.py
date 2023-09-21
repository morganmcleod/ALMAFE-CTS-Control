import unittest
import logging
import copy
import time
from CTSDevices.MotorControl.GalilDMCSocket import MotorController
from CTSDevices.MotorControl.schemas import MotorStatus, MoveStatus, Position

class test_GalilDMCSocket(unittest.TestCase):

    def setUp(self) -> None:
        self.mc = MotorController()
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.logger.setLevel(logging.DEBUG)
        return super().setUp()

    def tearDown(self) -> None:
        del self.mc
        self.logger = None
        return super().tearDown()
    
    def test_reset(self):
        self.mc.reset()
        self.assertTrue(self.mc.isConnected())
        self.assertEqual(self.mc.nextPos, Position(x=0, y=0, z=0))
        self.assertEqual(self.mc.position, Position(x=0, y=0, z=0))
        self.assertEqual(self.mc.motorStatus, MotorStatus())
        self.assertGreater(self.mc.xySpeed, 0)
        self.assertGreater(self.mc.polSpeed, 0)

    def Xtest_flush(self):
        pass

    def Xtest_sendall(self):
        pass

    def Xtest_recv(self):
        pass

    def Xtest_query(self):
        pass

    def test_isConnected(self):
        for i in range(100):
            with self.subTest():
                self.assertTrue(self.mc.isConnected())

    def Xtest_setXYSpeed(self):
        prev = self.mc.getXYSpeed()
        self.assertGreater(prev, 0)
        with self.subTest():
            self.mc.setXYSpeed(prev * 2)
            speed = self.mc.getXYSpeed()
            self.assertEqual(speed, prev * 2)
        self.mc.setXYSpeed(prev)
        speed = self.mc.getXYSpeed()
        self.assertEqual(speed, prev)
        
    def Xtest_setXYAccel(self):
        prev = self.mc.getXYAccel()
        self.assertGreater(prev, 0)
        with self.subTest():
            self.mc.setXYAccel(prev * 2)
            accel = self.mc.getXYAccel()
            self.assertEqual(accel, prev * 2)
        self.mc.setXYAccel(prev)
        accel = self.mc.getXYAccel()
        self.assertEqual(accel, prev)

    def Xtest_setXYDecel(self):
        prev = self.mc.getXYDecel()
        self.assertGreater(prev, 0)
        with self.subTest():
            self.mc.setXYDecel(prev * 2)
            decel = self.mc.getXYDecel()
            self.assertEqual(decel, prev * 2)
        self.mc.setXYDecel(prev)
        decel = self.mc.getXYDecel()
        self.assertEqual(decel, prev)

    def Xtest_setPolSpeed(self):
        prev = self.mc.getPolSpeed()
        self.assertGreater(prev, 0)
        with self.subTest():
            self.mc.setPolSpeed(prev * 2)
            speed = self.mc.getPolSpeed()
            self.assertEqual(speed, prev * 2)
        self.mc.setPolSpeed(prev)
        speed = self.mc.getPolSpeed()
        self.assertEqual(speed, prev)

    def Xtest_setPolAccel(self):
        prev = self.mc.getPolAccel()
        self.assertGreater(prev, 0)
        with self.subTest():
            self.mc.setPolAccel(prev * 2)
            accel = self.mc.getPolAccel()
            self.assertEqual(accel, prev * 2)
        self.mc.setPolAccel(prev)
        accel = self.mc.getPolAccel()
        self.assertEqual(accel, prev)

    def Xtest_setPolDecel(self):
        prev = self.mc.getPolDecel()
        self.assertGreater(prev, 0)
        with self.subTest():
            self.mc.setPolDecel(prev * 2)
            decel = self.mc.getPolDecel()
            self.assertEqual(decel, prev * 2)
        self.mc.setPolDecel(prev)
        decel = self.mc.getPolDecel()
        self.assertEqual(decel, prev)

    def test_getPolTorque(self):
        torque = self.mc.getPolTorque()
        self.logger.info(f"mc.getPolTorque returned {torque} Volts")
        pass

    def Xtest_homeAxis(self):
        self.assertFalse(self.mc.getMotorStatus().inMotion())

        XY_TIMEOUT = 20
        prevPos = self.mc.getPosition(cached = False)
        self.logger.info(f"test_homeAxis: prevPos = {prevPos.getText()}")

        self.logger.info("test_homeAxis: X")
        with self.subTest():
            toPos = copy.copy(prevPos)
            toPos.x = 0
            self.mc.homeAxis('x')
            motorStatus = self.mc.waitForMove(XY_TIMEOUT)
            pos = self.mc.getPosition(cached = False)
            self.assertEqual(pos.x, 0)
        
        self.mc.setNextPos(prevPos)
        self.mc.startMove(withTrigger = False)
        self.mc.waitForMove(XY_TIMEOUT)

        self.logger.info("test_homeAxis: Y")
        with self.subTest():
            toPos = copy.copy(prevPos)
            toPos.y = 0
            self.mc.homeAxis('y')
            motorStatus = self.mc.waitForMove(XY_TIMEOUT)
            pos = self.mc.getPosition(cached = False)
            self.assertEqual(pos.y, 0)
        
        self.mc.setNextPos(prevPos)
        self.mc.startMove(withTrigger = False)
        self.mc.waitForMove(XY_TIMEOUT)

        self.logger.info("test_homeAxis: XY")
        with self.subTest():
            toPos = copy.copy(prevPos)
            toPos.x = 0
            toPos.y = 0
            self.mc.homeAxis('xy')
            motorStatus = self.mc.waitForMove(XY_TIMEOUT)
            self.assertTrue(not motorStatus.inMotion() and not motorStatus.powerFail())
            pos = self.mc.getPosition(cached = False)
            self.assertEqual(pos.x, 0)
            self.assertEqual(pos.y, 0)

    def test_stopMove(self):
        self.assertFalse(self.mc.getMotorStatus().inMotion())
        
        prevPos = self.mc.getPosition(cached = False)
        toPos = Position(
            x = 50,
            y = 50,
            pol = prevPos.pol
        )
        timeout = self.mc.estimateMoveTime(prevPos, toPos)
        self.mc.setNextPos(toPos)
        self.mc.startMove()
        self.mc.waitForMove()

        prevPos = toPos
        toPos = Position(
            x = 100,
            y = 100,
            pol = prevPos.pol
        )
        timeout = self.mc.estimateMoveTime(prevPos, toPos)
        self.mc.setNextPos(toPos)
        self.mc.startMove()
        time.sleep(timeout / 4)
        self.mc.stopMove()
        time.sleep(0.5)
        self.assertFalse(self.mc.getMotorStatus().inMotion())
        pos = self.mc.getPosition(cached = False)
        self.assertNotEqual(pos, prevPos)
        self.assertNotEqual(pos, toPos)
        

    def Xtest_getMoveStatus(self):
        pass
