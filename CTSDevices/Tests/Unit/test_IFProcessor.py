import unittest
from CTSDevices.IFProcessor.Attenuator import Attenuator
from CTSDevices.IFProcessor.InputSwitch import InputSwitch, InputSelect
from CTSDevices.IFProcessor.NoiseSource import NoiseSource
from CTSDevices.IFProcessor.OutputSwitch import OutputSwitch, OutputSelect, LoadSelect
from CTSDevices.IFProcessor.YIGFilter import YIGFilter
import time

class test_IFProcessor(unittest.TestCase):

    def setUp(self):        
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
        print("test_Attenuator.reset()...")
        self.attenuator.reset()
        time.sleep(2)
        for atten in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 80):
            print(f"test_Attenuator.setValue({atten})...")
            self.attenuator.setValue(atten)
            time.sleep(2)
        print("test_Attenuator.reset()...")
        self.attenuator.reset()
        time.sleep(2)
        
    def Xtest_InputSwitch(self):
        for input in InputSelect:
            print(f"test_InputSwitch.setValue({input.name})...")
            self.inputSwitch.setValue(input)
            time.sleep(2)
        print("test_InputSwitch.setValue(POL0_USB)...")
        self.inputSwitch.setValue(InputSelect.POL0_USB)
        time.sleep(2)

    def Xtest_OutputSwitch(self):
        print("test_OutputSwitch.reset()...")
        self.outputSwitch.reset()
        time.sleep(2)
        print("test_OutputSwitch.setValue(POWER_METER, THROUGH)...")
        self.outputSwitch.setValue(OutputSelect.POWER_METER, LoadSelect.THROUGH)
        time.sleep(2)
        print("test_OutputSwitch.setValue(POWER_METER, LOAD)...")
        self.outputSwitch.setValue(OutputSelect.POWER_METER, LoadSelect.LOAD)
        time.sleep(2)
        print("test_OutputSwitch.setValue(SQUARE_LAW, THROUGH)...")
        self.outputSwitch.setValue(OutputSelect.SQUARE_LAW, LoadSelect.THROUGH)
        time.sleep(2)
        print("test_OutputSwitch.setValue(SQUARE_LAW, LOAD)...")
        self.outputSwitch.setValue(OutputSelect.SQUARE_LAW, LoadSelect.LOAD)
        time.sleep(2)
        print("test_OutputSwitch.reset()...")
        self.outputSwitch.reset()
        time.sleep(2)
        
    def Xtest_NoiseSource(self):
        print("test_NoiseSource.reset()...")
        self.noiseSource.reset()
        time.sleep(2)
        print("test_NoiseSource.setEnable(True)...")
        self.noiseSource.setEnable(True)
        time.sleep(2)
        print("test_NoiseSource.setEnable(False)...")
        self.noiseSource.setEnable(False)
        time.sleep(2)
        print("test_NoiseSource.setEnable(True)...")
        self.noiseSource.setEnable(True)
        time.sleep(2)
        print("test_NoiseSource.reset()...")
        self.noiseSource.reset()
        time.sleep(2)

    def test_YIGFilter(self):
        self.attenuator.setValue(10)
        print("test_YIGFilter.reset()...")
        self.yigFilter.reset()
        self.assertEqual(self.yigFilter.getFrequency(), 0)
        for i in range(9):
            freqGHz = (i + 4)  # 4..12 by 1 GHz
            print(f"test_YIGFilter.setFrequency({freqGHz})...")
            self.yigFilter.setFrequency(freqGHz)
            self.assertEqual(self.yigFilter.getFrequency(), freqGHz)
            time.sleep(2)        
        print("test_YIGFilter.reset()...")
        self.yigFilter.reset()
        self.assertEqual(self.yigFilter.getFrequency(), 0)
        