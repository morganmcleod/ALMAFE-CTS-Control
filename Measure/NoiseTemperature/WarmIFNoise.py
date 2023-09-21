from CTSDevices.WarmIFPlate.InputSwitch import InputSelect
from CTSDevices.WarmIFPlate.WarmIFPlate import WarmIFPlate
from CTSDevices.PowerMeter.KeysightE441X import PowerMeter, Unit
from CTSDevices.PowerSupply.AgilentE363xA import PowerSupply
from CTSDevices.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from DBBand6Cart.schemas.WarmIFNoise import DUT_Types, WarmIFNoise
from DBBand6Cart.WarmIFNoiseData import WarmIFNoiseData
from app.database.CTSDB import CTSDB
from DebugOptions import *

from .schemas import CommonSettings, WarmIFSettings

import concurrent.futures
import logging
import time
from typing import Tuple

class WarmIfNoise():

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
        self.database = WarmIFNoiseData(driver = CTSDB())
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers = 1)
        self.__reset()

    def __reset(self):
        self.commonSettings = None
        self.settings = None
        self.keyCartTest = 0
        self.stopNow = False
        self.finished = False
        self.rawData = []

    def start(self):
        self.stopNow = False
        self.finished = False
        self.futures = []
        self.futures.append(self.executor.submit(self.__run))

    def stop(self):
        self.stopNow = True

    def isMeasuring(self):
        return not self.finished

    def __run(self):
        self.powerSupply.setOutputEnable(False)
        self.powerSupply.setVoltage(self.settings.diodeVoltage)
        self.powerSupply.setCurrentLimit(self.settings.diodeCurrentLimit)
        self.powerMeter.setUnits(Unit.DBM)
        self.warmIFPlate.inputSwitch.setValue(InputSelect.NOISE_DIODE)
        if self.stopNow:
            self.finished = True
            self.logger.info("User stop")
            return
        
        ifSteps = [
            self.settings.ifStart + i * self.settings.ifStep 
            for i in range(int((self.settings.ifStop - self.settings.ifStart) / self.settings.ifStep + 1))
        ]
        attenSteps = [
            self.settings.attenStart + i * self.settings.attenStep 
            for i in range(int((self.settings.attenStop - self.settings.attenStart) / self.settings.attenStep + 1))
        ]
        for freq in ifSteps:
            self.warmIFPlate.yigFilter.setFrequency(freq)
            for atten in attenSteps:
                self.warmIFPlate.attenuator.setValue(atten)

                if self.stopNow:
                    self.finished = True
                    self.logger.info("User stop")
                    return

                self.powerSupply.setOutputEnable(True)
                time.sleep(0.25)
                pHot = self.powerMeter.autoRead()
                self.powerSupply.setOutputEnable(False)
                time.sleep(0.25)
                pCold = self.powerMeter.autoRead()
                temps, errors = self.temperatureMonitor.readAll()
                ambient = temps[self.commonSettings.sensorAmbient - 1]
                tIFHot = temps[self.settings.sensorIfHot - 1]
                tIFCold = temps[self.settings.sensorIfCold - 1]
                record = WarmIFNoise(
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
                )
                if not SIMULATE:
                    self.database.create(record)
                else:
                    record.id = int(freq * 100 + atten)                
                self.rawData.append(record)
        self.finished = True
