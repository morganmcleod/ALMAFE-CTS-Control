import unittest
from CTSDevices.TemperatureMonitor.Lakeshore218 import *
import time

class test_Lakeshore218(unittest.TestCase):
    
    DO_PRINT = False

    def setUp(self):        
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.inst = TemperatureMonitor()
        time.sleep(0.2)
                
    def tearDown(self):
        del self.inst
        self.inst = None

    def test_idQuery(self):
        ret = self.inst.idQuery()
        self.assertTrue(ret)

    def test_reset(self):
        ret = self.inst.reset()
        self.assertTrue(ret)

    def test_readSingle(self):
        for i in range(8):
            temp, err = self.inst.readSingle(i + 1)
            self.assertTrue(isinstance(err, int))
            self.assertTrue(isinstance(temp, float))
            if err == 0:
                self.assertTrue(temp > 0)
            else:
                self.assertEqual(temp, -1)


    def test_readAll(self):
        temps, errors = self.inst.readAll()
        self.assertTrue(len(temps) == 8)
        self.assertTrue(len(errors) == 8)
        for temp, err in zip(temps, errors):
            self.assertTrue(isinstance(temp, float))
            self.assertTrue(isinstance(err, int))
            if err == 0:
                self.assertTrue(temp > 0)
            else:
                self.assertEqual(temp, -1)
