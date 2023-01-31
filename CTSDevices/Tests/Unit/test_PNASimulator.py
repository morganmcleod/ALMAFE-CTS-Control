import unittest
from CTSDevices.PNA.PNAInterface import *
from CTSDevices.PNA.PNASimulator import *

class test_PNASimulator(unittest.TestCase):

    def setUp(self):        
        self.pna = PNASimulator()
                
    def tearDown(self):
        del self.pna
        self.pna = None

    def test_idQuery(self):
        pass
    
    def test_reset(self):
        pass
    
    def test_setMeasConfig(self):
        self.pna.setMeasConfig(MeasConfig(
            channel = 1,
            measType = MeasType.S21,
            format = Format.SDATA,
            sweepType = SweepType.CW_TIME,
            sweepGenType = SweepGenType.STEPPED,
            sweepPoints = 401,
            triggerSource = TriggerSource.IMMEDIATE,
            bandWidthHz = 200,
            centerFreq_Hz = 10.180e9,
            spanFreq_Hz = 0,
            timeout_sec = 6.03,
            sweepTimeAuto = True,
            measName = "CH1_S21_CW"
        ))

    def test_setPowerConfig(self):
        self.pna.setPowerConfig(PowerConfig())
    
    def test_getTrace(self):
        self.pna.setMeasConfig(MeasConfig(
            channel = 1,
            measType = MeasType.S21,
            format = Format.SDATA,
            sweepType = SweepType.CW_TIME,
            sweepGenType = SweepGenType.STEPPED,
            sweepPoints = 401,
            triggerSource = TriggerSource.IMMEDIATE,
            bandWidthHz = 200,
            centerFreq_Hz = 10.180e9,
            spanFreq_Hz = 0,
            timeout_sec = 6.03,
            sweepTimeAuto = True,
            measName = "CH1_S21_CW"
        ))
        self.pna.setPowerConfig(PowerConfig())
        amp, phase = self.pna.getTrace()
        self.assertEqual(len(amp), 401)
        self.assertEqual(len(phase), 401)
        
    def test_getAmpPhase(self):
        self.pna.setMeasConfig(MeasConfig(
            channel = 1,
            measType = MeasType.S21,
            format = Format.SDATA,
            sweepType = SweepType.CW_TIME,
            sweepGenType = SweepGenType.STEPPED,
            sweepPoints = 20,
            triggerSource = TriggerSource.IMMEDIATE,
            bandWidthHz = 200,
            centerFreq_Hz = 10.180e9,
            spanFreq_Hz = 0,
            timeout_sec = 6.03,
            sweepTimeAuto = True,
            measName = "CH1_S21_CW"
        ))
        self.pna.setPowerConfig(PowerConfig())
        amp, phase = self.pna.getAmpPhase()
      
