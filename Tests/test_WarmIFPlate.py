import unittest
from AMB.AMBConnectionDLL import AMBConnectionDLL
from AMB.LODevice import LODevice
from AMB.CCADevice import CCADevice
from Controllers.Receiver.CartAssembly import CartAssembly
from INSTR.WarmIFPlate.Attenuator import Attenuator
from INSTR.InputSwitch.InputSwitch import InputSwitch, InputSelect
from INSTR.WarmIFPlate.NoiseSource import NoiseSource
from INSTR.WarmIFPlate.OutputSwitch import OutputSwitch, OutputSelect, LoadSelect
from INSTR.WarmIFPlate.YIGFilter import YIGFilter
import configparser
import time
import logging

CARTRIDGE_BAND = 6
YTO_LOW = 12.22
YTO_HIGH = 14.77
CARTRIDGE_CONFIG = 433

class test_WarmIFPlate(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        config = configparser.ConfigParser()
        config.read('FrontEndAMBDLL.ini')
        dllName = config['load']['dll']
        cls.conn = AMBConnectionDLL(channel = 0, dllName = dllName)
        cls.ccaDevice = CCADevice(cls.conn, nodeAddr = 0x13, band = CARTRIDGE_BAND)
        cls.ccaDevice.setFeMode(cls.ccaDevice.MODE_TROUBLESHOOTING)
        cls.ccaDevice.setBandPower(CARTRIDGE_BAND, True)

        cls.loDevice = LODevice(cls.conn, nodeAddr = 0x13, band = CARTRIDGE_BAND)
        cls.ccaDevice.setFeMode(cls.ccaDevice.MODE_TROUBLESHOOTING)
        cls.loDevice.setBandPower(CARTRIDGE_BAND, True)
        cls.loDevice.setYTOLimits(YTO_LOW, YTO_HIGH)

        cls.cartAssembly = CartAssembly(cls.ccaDevice, cls.loDevice, CARTRIDGE_CONFIG)
        cls.ccaDevice.setFeMode(cls.ccaDevice.MODE_TROUBLESHOOTING)
        cls.cartAssembly.setBias(241)
        cls.cartAssembly.autoLOPower()

    @classmethod
    def tearDownClass(cls):
        cls.ccaDevice.shutdown()
        cls.loDevice.shutdown()
        cls.conn.shutdown()

    def setUp(self):
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.attenuator = Attenuator()
        self.inputSwitch = InputSwitch()
        self.noiseSource = NoiseSource()
        self.outputSwitch = OutputSwitch()
        self.yigFilter = YIGFilter()
        
    def tearDown(self):
        self.__implErrorQuery()
        del self.attenuator
        self.attenuator = None
        del self.inputSwitch
        self.inputSwitch = None
        del self.noiseSource
        self.noiseSource = None
        del self.outputSwitch
        self.outputSwitch = None
        del self.yigFilter
        self.yigFilter = None
                
    def __implErrorQuery(self):
        return 0, ""

    def Xtest_Attenuator(self):
        self.logger.info("test_Attenuator.reset()...")
        self.attenuator.reset()
        time.sleep(2)
        for atten in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 80):
            self.logger.info(f"test_Attenuator.setValue({atten})...")
            self.attenuator.setValue(atten)
            time.sleep(2)
        self.logger.info("test_Attenuator.reset()...")
        self.attenuator.reset()
        time.sleep(2)
        
    def Xtest_InputSwitch(self):
        for input in InputSelect:
            self.logger.info(f"test_InputSwitch.setValue({input.name})...")
            self.inputSwitch.setValue(input)
            time.sleep(2)
        self.logger.info("test_InputSwitch.setValue(POL0_USB)...")
        self.inputSwitch.setValue(InputSelect.POL0_USB)
        time.sleep(2)

    def test_OutputSwitch(self):
        self.logger.info("test_OutputSwitch.reset()...")
        self.outputSwitch.reset()
        time.sleep(2)
        self.logger.info("test_OutputSwitch.setValue(POWER_METER, THROUGH)...")
        self.outputSwitch.setValue(OutputSelect.POWER_METER, LoadSelect.THROUGH)
        time.sleep(2)
        self.logger.info("test_OutputSwitch.setValue(POWER_METER, LOAD)...")
        self.outputSwitch.setValue(OutputSelect.POWER_METER, LoadSelect.LOAD)
        time.sleep(2)
        self.logger.info("test_OutputSwitch.setValue(SQUARE_LAW, THROUGH)...")
        self.outputSwitch.setValue(OutputSelect.SQUARE_LAW, LoadSelect.THROUGH)
        time.sleep(2)
        self.logger.info("test_OutputSwitch.setValue(SQUARE_LAW, LOAD)...")
        self.outputSwitch.setValue(OutputSelect.SQUARE_LAW, LoadSelect.LOAD)
        time.sleep(2)
        self.logger.info("test_OutputSwitch.reset()...")
        self.outputSwitch.reset()
        time.sleep(2)
        
    def Xtest_NoiseSource(self):
        self.logger.info("test_NoiseSource.reset()...")
        self.noiseSource.reset()
        time.sleep(2)
        self.logger.info("test_NoiseSource.setEnable(True)...")
        self.noiseSource.setEnable(True)
        time.sleep(2)
        self.logger.info("test_NoiseSource.setEnable(False)...")
        self.noiseSource.setEnable(False)
        time.sleep(2)
        self.logger.info("test_NoiseSource.setEnable(True)...")
        self.noiseSource.setEnable(True)
        time.sleep(2)
        self.logger.info("test_NoiseSource.reset()...")
        self.noiseSource.reset()
        time.sleep(2)

    def Xtest_YIGFilter(self):
        self.attenuator.setValue(10)
        self.logger.info("test_YIGFilter.reset()...")
        self.yigFilter.reset()
        self.assertEqual(self.yigFilter.getFrequency(), self.yigFilter.minGHz)
        for freqGHz in (4, 5, 6, 7, 8, 9, 10, 11, 12):
            self.logger.info(f"test_YIGFilter.setFrequency({freqGHz})...")
            self.yigFilter.setFrequency(freqGHz)
            self.assertEqual(self.yigFilter.getFrequency(), freqGHz)
            time.sleep(2)        
        self.logger.info("test_YIGFilter.reset()...")
        self.yigFilter.reset()
        self.assertEqual(self.yigFilter.getFrequency(), self.yigFilter.minGHz)
        