from CTSDevices.WarmIFPlate.InputSwitch import InputSelect, InputSwitch
from CTSDevices.WarmIFPlate.OutputSwitch import PadSelect, LoadSelect, OutputSelect
from CTSDevices.WarmIFPlate.WarmIFPlate import WarmIFPlate
from CTSDevices.PowerMeter.KeysightE441X import PowerMeter, Unit
from CTSDevices.PowerSupply.AgilentE363xA import PowerSupply
from CTSDevices.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from DBBand6Cart.schemas.WarmIFNoise import DUT_Types, WarmIFNoise
from DBBand6Cart.WarmIFNoiseData import WarmIFNoiseData
from app.database.CTSDB import CTSDB
from DebugOptions import *

import concurrent.futures
import logging
import time
from typing import Tuple

class MeasureWarmIFNoise():

    ATTEN_START = 0
    ATTEN_STOP = 10
    ATTEN_STEP = 1
    FREQ_START = 4.0
    FREQ_STOP = 12.0
    FREQ_STEP = 0.1
    SENSOR_AMBIENT = 7
    SENSOR_IFHOT = 1
    SENSOR_IFCOLD = 3
    DIODE_VOLTAGE = 28.0
    DIODE_CURRENT_LIMIT = 0.04
    DIODE_ENR = 15.4

    def __init__(self, 
            warmIFPlate: WarmIFPlate, 
            powerMeter: PowerMeter,
            powerSupply: PowerSupply,
            temperatureMonitor: TemperatureMonitor):
        
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.warmIFPlate = warmIFPlate
        self.powerMeter = powerMeter
        self.powerSupply = powerSupply
        self.temperatureMonitor = temperatureMonitor
        self.warmIFNoiseData = WarmIFNoiseData(driver = CTSDB())
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers = 1)
        self.keyCartTest = 0
        self.__reset()

    def __reset(self):
        self.stopNow = False

    def start(self):
        self.stopNow = False
        self.futures = []
        self.futures.append(self.executor.submit(self.__run))

    def stop(self):
        self.stopNow = True

    def __run(self):
        self.powerSupply.setOutputEnable(False)
        self.powerSupply.setVoltage(self.DIODE_VOLTAGE)
        self.powerSupply.setCurrentLimit(self.DIODE_CURRENT_LIMIT)
        self.powerMeter.setUnits(Unit.W)
        self.warmIFPlate.inputSwitch.setValue(InputSelect.NOISE_DIODE)
        if self.stopNow:
            self.__abort("User Stop")
            return
        
        freqs = [self.FREQ_START + i * self.FREQ_STEP for i in range(int((self.FREQ_STOP - self.FREQ_START) / self.FREQ_STEP + 1))]
        attens = [self.ATTEN_START + i * self.ATTEN_STEP for i in range(int((self.ATTEN_STOP - self.ATTEN_START) / self.ATTEN_STEP + 1))]
        for freq in freqs:
            self.warmIFPlate.yigFilter.setFrequency(freq)
            for atten in attens:
                self.warmIFPlate.attenuator.setValue(atten)

                if self.stopNow:
                    self.__abort("User Stop")
                    return

                self.powerSupply.setOutputEnable(True)
                time.sleep(0.25)
                pHot = self.powerMeter.autoRead()
                self.powerSupply.setOutputEnable(False)
                time.sleep(0.25)
                pCold = self.powerMeter.autoRead()
                temps, errors = self.temperatureMonitor.readAll()
                ambient = temps[self.SENSOR_AMBIENT - 1]
                tIFHot = temps[self.SENSOR_IFHOT - 1]
                tIFCold = temps[self.SENSOR_IFCOLD - 1]
                if not SIMULATE:
                    self.warmIFNoiseData.create(WarmIFNoise(
                        fkCartTest = self.keyCartTest,
                        fkDUT_Type = DUT_Types.BAND6_CARTRIDGE,
                        freqYig = freq,
                        atten = atten,
                        pHot = pHot,
                        pCold = pCold,
                        tAmbient = ambient,
                        tIFHot = tIFHot,
                        tIFCold = tIFCold,
                        noiseDiodeENR = self.DIODE_ENR
                    ))
        
    def __abort(self, msg) -> Tuple[bool, str]:
        self.logger.info(msg)
        return (False, msg)