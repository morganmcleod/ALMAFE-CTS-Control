import unittest
from CTSDevices.PowerMeter.BaseE441X import Channel, Trigger, Unit
from CTSDevices.PowerMeter.KeysightE441X import PowerMeter, StdErrConfig

class test_PowerMeter(unittest.TestCase):
    
    def setUp(self):        
        self.pm = PowerMeter()
        self.pm.twoChannel = False
        
    def tearDown(self):
        self.__implErrorQuery()
        del self.pm
        self.pm = None

    def __implErrorQuery(self):
        code, msg = self.pm.errorQuery()
        if not code:
            return False
        while code:
            print(code, msg)
            code, msg = self.pm.errorQuery()
        return True

    def test_setDefaults(self):
        self.assertTrue(self.pm.setDefaults())
        
    def test_reset(self):
        self.assertTrue(self.pm.reset())
        
    def test_idQuery(self):
        self.assertTrue(self.pm.idQuery(True))
        
    def test_errorQuery(self):
        self.assertFalse(self.__implErrorQuery())

    def test_setUnits(self):
        self.assertTrue(self.pm.setUnits(Unit.W, Channel.A))
        self.assertTrue(self.pm.setUnits(Unit.DBM, Channel.A))
        if self.pm.twoChannel:
            self.assertTrue(self.pm.setUnits(Unit.W, Channel.B))
            self.assertTrue(self.pm.setUnits(Unit.DBM, Channel.B))

    def test_setFastMode(self):
        self.assertTrue(self.pm.setFastMode(True, Channel.A))
        self.assertTrue(self.pm.setFastMode(False, Channel.A))
        if self.pm.twoChannel:
            self.assertTrue(self.pm.setFastMode(True, Channel.B))
            self.assertTrue(self.pm.setFastMode(False, Channel.B))

    def test_zero(self):
        self.assertTrue(self.pm.zero(Channel.A))
        if self.pm.twoChannel:
            self.assertTrue(self.pm.zero(Channel.B))

    def test_setOutputRef(self):
        self.assertTrue(self.pm.setOutputRef(True))
        self.assertTrue(self.pm.setOutputRef(False))
        
    def test_read(self):
        self.pm.configureTrigger(Trigger.IMMEDIATE, Channel.A)
        self.pm.configMeasurement(Channel.A, units = Unit.DBM)
        val = self.pm.read(Channel.A)
        self.assertTrue(val != 0.0)
        if self.pm.twoChannel:
            self.pm.configureTrigger(Trigger.IMMEDIATE, Channel.B)
            self.pm.configMeasurement(Channel.B, units = Unit.DBM)
            val = self.pm.read(Channel.B)
            self.assertTrue(val != 0.0)

    def test_simpleRead(self):
        val = self.pm.simpleRead(Channel.A)
        self.assertTrue(val != 0.0)
        if self.pm.twoChannel:
            val = self.pm.simpleRead(Channel.B)
            self.assertTrue(val != 0.0)

    def test_autoRead(self):
        val = self.pm.autoRead(Channel.A)
        self.assertTrue(val != 0.0)
        if self.pm.twoChannel:
            val = self.pm.autoRead(Channel.B)
            self.assertTrue(val != 0.0)

    def test_averagingRead_MIN_SAMPLES(self):
        config = StdErrConfig(
            minS = 5,
            maxS = 0,
            stdErr = 0,
            timeout = 0
        )
        result = self.pm.averagingRead(config, Channel.A)
        self.assertEqual(result.useCase, StdErrConfig.UseCase.MIN_SAMPLES)
        self.assertEqual(result.N, 5)
        self.assertNotEqual(result.stdErr, 0)
        self.assertNotEqual(result.CI95U, 0)
        self.assertNotEqual(result.CI95L, 0)
        self.assertGreater(result.time, 0)

    def test_averagingRead_MAX_SAMPLES(self):
        config = StdErrConfig(
            minS = 5,
            maxS = 20,
            stdErr = 0.001,
            timeout = 0
        )
        result = self.pm.averagingRead(config, Channel.A)
        self.assertEqual(result.useCase, StdErrConfig.UseCase.MAX_SAMPLES)
        self.assertEqual(result.N, 20)
        self.assertNotEqual(result.stdErr, 0)
        self.assertNotEqual(result.CI95U, 0)
        self.assertNotEqual(result.CI95L, 0)
        self.assertGreater(result.time, 0)

    def test_averagingRead_MIN_TO_TIMEOUT(self):
        config = StdErrConfig(
            minS = 5,
            maxS = 0,
            stdErr = 0.001,
            timeout = 10
        )
        result = self.pm.averagingRead(config, Channel.A)
        self.assertEqual(result.useCase, StdErrConfig.UseCase.MIN_TO_TIMEOUT)
        self.assertGreater(result.N, 5)
        self.assertNotEqual(result.stdErr, 0)
        self.assertNotEqual(result.CI95U, 0)
        self.assertNotEqual(result.CI95L, 0)
        self.assertGreater(result.time, 10)

    def test_averagingRead_MOVING_WINDOW(self):
        config = StdErrConfig(
            minS = 5,
            maxS = 20,
            stdErr = 0.001,
            timeout = 10
        )
        result = self.pm.averagingRead(config, Channel.A)
        self.assertEqual(result.useCase, StdErrConfig.UseCase.MOVING_WINDOW)
        self.assertGreater(result.N, 20)
        self.assertNotEqual(result.stdErr, 0)
        self.assertNotEqual(result.CI95U, 0)
        self.assertNotEqual(result.CI95L, 0)
        self.assertGreater(result.time, 10)

    def test_averagingRead_TIMEOUT(self):
        config = StdErrConfig(
            minS = 0,
            maxS = 0,
            stdErr = 0,
            timeout = 3
        )
        result = self.pm.averagingRead(config, Channel.A)
        self.assertEqual(result.useCase, StdErrConfig.UseCase.TIMEOUT)
        self.assertGreater(result.N, 0)
        self.assertNotEqual(result.stdErr, 0)
        self.assertNotEqual(result.CI95U, 0)
        self.assertNotEqual(result.CI95L, 0)
        self.assertGreater(result.time, 3)
