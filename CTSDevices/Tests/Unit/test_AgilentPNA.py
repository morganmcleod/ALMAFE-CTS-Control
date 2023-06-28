import unittest
from CTSDevices.PNA.schemas import *
from CTSDevices.PNA.PNAInterface import *
from CTSDevices.PNA.BaseAgilentPNA import *
from CTSDevices.PNA.AgilentPNA import *

class test_AgilentPNA(unittest.TestCase):
    
    DO_PRINT = False

    def setUp(self):        
        self.pna = AgilentPNA()
        # clear any previous errors:
        self.__implErrorQuery()
        self.__implWorkaroundPhaseLockLost()
        self.pna.setMeasConfig(DEFAULT_CONFIG)
                
    def tearDown(self):
        # clear any errors not detected by test case:
        self.__implErrorQuery()
        del self.pna
        self.pna = None

    def __implErrorQuery(self):
        code, msg = self.pna.errorQuery()
        if not code:
            return False
        while code:
            if self.DO_PRINT:
                print(code, msg)
            code, msg = self.pna.errorQuery()
        return True
    
    def __implWorkaroundPhaseLockLost(self):
        self.pna.configureFreqCenterSpan(
            channel = 1,
            centerFreq_Hz = 6e9,
            spanFreq_Hz = 12e9
        )
        self.__implErrorQuery()

    def test_errorQuery(self):
        self.assertFalse(self.__implErrorQuery())

    def test_setMeasConfig(self):
        self.pna.setMeasConfig(DEFAULT_CONFIG)
        self.assertFalse(self.__implErrorQuery())
        self.assertTrue(self.pna.checkDisplayTrace())
        self.assertFalse(self.__implErrorQuery())
        self.assertTrue(self.pna.checkDisplayWindow())
        self.assertFalse(self.__implErrorQuery())
        measList = self.pna.listMeasurementParameters()
        self.assertTrue(len(measList) > 0)
        self.assertTrue(measList[0] == DEFAULT_CONFIG.measName)
        self.assertFalse(self.__implErrorQuery())

    def test_setPowerConfig(self):
        self.pna.setPowerConfig(DEFAULT_POWER_CONFIG)
        self.assertFalse(self.__implErrorQuery())

    def test_getTrace(self):
        config = DEFAULT_CONFIG
        config.sweepPoints = 401
        # config.timeout_sec = 60
        self.pna.setMeasConfig(config)
        self.assertFalse(self.__implErrorQuery())
        self.pna.setPowerConfig(DEFAULT_POWER_CONFIG)
        self.assertFalse(self.__implErrorQuery())
        amp, phase = self.pna.getTrace()
        self.assertFalse(self.__implErrorQuery())
        self.assertEqual(len(amp), 401)
        self.assertEqual(len(phase), 401)

    def test_getAmpPhase(self):
        self.pna.setMeasConfig(FAST_CONFIG)
        self.assertFalse(self.__implErrorQuery())
        self.pna.setPowerConfig(DEFAULT_POWER_CONFIG)
        self.assertFalse(self.__implErrorQuery())
        for _ in range(10):
            amp, phase = self.pna.getAmpPhase()
            if self.DO_PRINT:
                print(f"amplitude={amp} phase={phase}")
            self.assertFalse(self.__implErrorQuery())
        
    def test_idQuery(self):
        self.assertTrue(self.pna.idQuery(doPrint = self.DO_PRINT))
        self.assertFalse(self.__implErrorQuery())
        
    def test_reset(self):
        self.assertTrue(self.pna.reset())
        self.assertFalse(self.__implErrorQuery())
        
    def test_listMeasurementParameters(self):
        params = self.pna.listMeasurementParameters(doPrint = self.DO_PRINT)
        self.assertFalse(self.__implErrorQuery())
        self.assertTrue(params)

    def test_configureMeasurementParameter(self):
        self.__implWorkaroundPhaseLockLost()

        name = 'test_configureMeasurementParameter'
        self.pna.configureMeasurementParameter(
            channel = 1, 
            mode = Mode.CREATE, 
            measType = MeasType.S21,
            measName = name
        )
        self.assertFalse(self.__implErrorQuery())
        params = self.pna.listMeasurementParameters()

        self.__implWorkaroundPhaseLockLost()

        self.assertFalse(self.__implErrorQuery())
        self.assertTrue(name in params)
        self.pna.configureMeasurementParameter(
            channel = 1, 
            mode = Mode.SELECT, 
            measName = name
        )
        self.assertFalse(self.__implErrorQuery())    #TODO: not passing "143 Phase lock has been lost"
                                                     # DONE: set the freq stop below 12 GHz and clear errors before CREATE
        params = self.pna.listMeasurementParameters()
        self.assertFalse(self.__implErrorQuery())
        self.assertTrue(name in params)
        self.pna.configureMeasurementParameter(
            channel = 1, 
            mode = Mode.DELETE, 
            measName = name
        )
        self.assertFalse(self.__implErrorQuery())
        params = self.pna.listMeasurementParameters()
        self.assertFalse(name in params)

    def test_checkDisplayTrace(self):
        self.assertTrue(self.pna.checkDisplayTrace())
        self.assertFalse(self.__implErrorQuery())

    def test_configureDisplayTrace(self):
        self.__implWorkaroundPhaseLockLost()

        name = "test_configureDisplayTrace"
        # if the window doesn't exist, create it:
        if not self.pna.checkDisplayWindow(1):
            self.pna.configureDisplayWindow(Mode.CREATE, 1)

        # delete then re-create the measurement:
        measNames = self.pna.listMeasurementParameters(channel = 1)
        if measNames:
            self.pna.configureMeasurementParameter(
                channel = 1,
                mode = Mode.DELETE, 
                measName = measNames[0]
            )
        self.pna.configureMeasurementParameter(
            channel = 1,
            mode = Mode.CREATE,
            measType = MeasType.S21,
            measName = name
        )

        self.pna.configureDisplayTrace(
            mode = Mode.CREATE,
            displayWindow = 1,
            displayTrace = 1,
            measName = name
        )
        self.assertFalse(self.__implErrorQuery())    #TODO: not passing "106 Requested measurement not found"
                                                     # DONE?: need to create the display window first?
        self.pna.configureDisplayTrace(
            mode = Mode.DELETE,
            displayWindow = 1,
            displayTrace = 1,
            measName = name
        )
        self.assertFalse(self.__implErrorQuery())

    def test_configureSweep(self):
        self.pna.configureSweep(
            channel = 1,
            sweepType = SweepType.LIN_FREQ,
            sweepGenType = SweepGenType.ANALOG,
            sweepOrDwellTime = 6.03,
            sweepPoints = 201,
            sweepTimeAuto = True
        )
        self.assertFalse(self.__implErrorQuery())

    def test_checkDisplayWindow(self):
        self.assertTrue(self.pna.checkDisplayWindow(1))
        self.assertFalse(self.__implErrorQuery())

    def test_configureDisplayWindow(self):
        # if the window exists, delete it:
        if self.pna.checkDisplayWindow(1):
            self.pna.configureDisplayWindow(Mode.DELETE, 1)

        name = "test_configureDisplayWindow"
        self.pna.configureDisplayWindow(
            mode = Mode.CREATE,
            displayWindow = 1,
            displayTitle = name
        )
        self.assertFalse(self.__implErrorQuery())    #TODO: not passing  "100 Duplicate window number"
                                                     # DONE?: need to delete the display window first?
        self.pna.configureDisplayWindow(
            mode = Mode.DELETE,
            displayWindow = 1,
            displayTitle = name
        )
        self.assertFalse(self.__implErrorQuery())

    def test_configureBandwidth(self):
        self.pna.configureBandwidth(channel = 1, bandWidthHz = 321)
        self.assertFalse(self.__implErrorQuery())

    def test_configureFreqCenterSpan(self):
        self.pna.configureFreqCenterSpan(channel = 1, centerFreq_Hz = 6e9, spanFreq_Hz = 500e6)
        self.assertFalse(self.__implErrorQuery())

    def test_setTriggerSweepSignal(self):
        self.pna.setTriggerSweepSignal(
            source = TriggerSource.IMMEDIATE,
            scope = TriggerScope.ALL_CHANNELS,
            level = TriggerLevel.HIGH,
            delaySeconds = 0.0005
        )
        self.assertFalse(self.__implErrorQuery())
        self.pna.setTriggerSweepSignal(
            source = TriggerSource.MANUAL,
            scope = TriggerScope.CURRENT_CHANNEL,
            level = TriggerLevel.HIGH,
            delaySeconds = 0.0005
        )
        self.assertFalse(self.__implErrorQuery())
        self.pna.setTriggerSweepSignal(
            source = TriggerSource.EXTERNAL,
            scope = TriggerScope.ALL_CHANNELS,
            level = TriggerLevel.HIGH,
            delaySeconds = 0.0005
        )
        self.assertFalse(self.__implErrorQuery())

    def test_configureTriggerChannel(self):
        self.pna.configureTriggerChannel(
            channel = 1,
            triggerPoint = True,
            mode = TriggerMode.CONTINUOUS,
            count = 1
        )
        self.assertFalse(self.__implErrorQuery())

    def test_configurePowerAttenuation(self):
        self.pna.configurePowerAttenuation(
            channel = 1,
            attenuation = 0
        )
        self.assertFalse(self.__implErrorQuery())

    def test_configurePowerLevel(self):
        self.pna.configurePowerLevel(
            channel = 1, 
            level = -15
        )
        self.assertFalse(self.__implErrorQuery())

    def test_configurePowerState(self):
        self.pna.configurePowerState(True)
        self.assertFalse(self.__implErrorQuery())
        self.pna.configurePowerState(False)
        self.assertFalse(self.__implErrorQuery())

    def test_generateTriggerSignal(self):
        self.pna.setTriggerSweepSignal(source = TriggerSource.MANUAL)

        self.pna.generateTriggerSignal(channel = 1, mode = True)
        self.assertFalse(self.__implErrorQuery())    #TODO: not passing  "-213 Init ignored"
                                                     # DONE?: set MANUAL trigger
        self.pna.generateTriggerSignal(channel = 1, mode = False)
        self.assertFalse(self.__implErrorQuery())

    def test_setDataFormat(self):
        self.pna.setDataFormat(format = DataFormat.REAL32, order = DataOrder.NORMAL)
        self.assertFalse(self.__implErrorQuery())
        self.pna.setDataFormat(format = DataFormat.REAL64, order = DataOrder.NORMAL)
        self.assertFalse(self.__implErrorQuery())
        self.pna.setDataFormat(format = DataFormat.ASCII, order = DataOrder.NORMAL)
        self.assertFalse(self.__implErrorQuery())

    def test_getDataFormat(self):
        self.pna.setDataFormat(format = DataFormat.REAL32, order = DataOrder.NORMAL)
        format = self.pna.getDataFormat()
        self.assertTrue(format == DataFormat.REAL32)
        self.pna.setDataFormat(format = DataFormat.REAL64, order = DataOrder.NORMAL)
        format = self.pna.getDataFormat()
        self.assertTrue(format == DataFormat.REAL64)
        self.pna.setDataFormat(format = DataFormat.ASCII, order = DataOrder.NORMAL)
        format = self.pna.getDataFormat()
        self.assertTrue(format == DataFormat.ASCII)

