from CTSDevices.WarmIFPlate.InputSwitch import InputSelect
from CTSDevices.WarmIFPlate.WarmIFPlate import WarmIFPlate
from CTSDevices.PowerMeter.KeysightE441X import PowerMeter, Unit
from CTSDevices.PowerSupply.AgilentE363xA import PowerSupply
from CTSDevices.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from DBBand6Cart.schemas.WarmIFNoise import DUT_Types, WarmIFNoise
from DBBand6Cart.WarmIFNoiseData import WarmIFNoiseData
from app.database.CTSDB import CTSDB
from DebugOptions import *

from .schemas import WarmIFSettings

import logging
import time
from typing import Tuple

class MeasureWarmIfNoise():

    def __init__(self, 
            warmIFPlate: WarmIFPlate, 
            powerMeter: PowerMeter,
            powerSupply: PowerSupply,
            temperatureMonitor: TemperatureMonitor,
            settings: WarmIFSettings):
        
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.warmIFPlate = warmIFPlate
        self.powerMeter = powerMeter
        self.powerSupply = powerSupply
        self.temperatureMonitor = temperatureMonitor
        self.settings = settings
        self.warmIFNoiseData = WarmIFNoiseData(driver = CTSDB())
        self.keyCartTest = 0
        self.stopNow = False
        self.finished = False

    def start(self):
        self.stopNow = False
        self.finished = False
        self.__run()
        self.finished = True

    def stop(self):
        self.stopNow = True

    def finished(self):
        return self.finished

    def __run(self):
        self.powerSupply.setOutputEnable(False)
        self.powerSupply.setVoltage(self.settings.diodeVoltage)
        self.powerSupply.setCurrentLimit(self.settings.diodeCurrentLimit)
        self.powerMeter.setUnits(Unit.W)
        self.warmIFPlate.inputSwitch.setValue(InputSelect.NOISE_DIODE)
        if self.stopNow:
            self.logger.info("User stop")
            return
        
        ifSteps = [self.settings.ifStart + i * self.settings.ifStep for i in range(int((self.settings.ifStop - self.settings.ifStart) / self.settings.ifStep + 1))]
        attenSteps = [self.settings.attenStart + i * self.settings.attenStep for i in range(int((self.settings.attenStop - self.settings.attenStart) / self.settings.attenStep + 1))]
        for freq in ifSteps:
            self.warmIFPlate.yigFilter.setFrequency(freq)
            for atten in attenSteps:
                self.warmIFPlate.attenuator.setValue(atten)

                if self.stopNow:
                    self.logger.info("User stop")
                    return

                self.powerSupply.setOutputEnable(True)
                time.sleep(0.25)
                pHot = self.powerMeter.autoRead()
                self.powerSupply.setOutputEnable(False)
                time.sleep(0.25)
                pCold = self.powerMeter.autoRead()
                temps, errors = self.temperatureMonitor.readAll()
                ambient = temps[self.settings.sensorAmbient - 1]
                tIFHot = temps[self.settings.sensorIfHot - 1]
                tIFCold = temps[self.settings.sensorIfCold - 1]
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
                        noiseDiodeENR = self.settings.diodeEnr
                    ))
