from CTSDevices.WarmIFPlate.InputSwitch import InputSelect
from CTSDevices.WarmIFPlate.OutputSwitch import OutputSelect, LoadSelect, PadSelect
from CTSDevices.WarmIFPlate.WarmIFPlate import WarmIFPlate
from CTSDevices.PowerMeter.KeysightE441X import PowerMeter, Unit
from CTSDevices.PowerSupply.AgilentE363xA import PowerSupply
from CTSDevices.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from DBBand6Cart.schemas.WarmIFNoise import DUT_Types, WarmIFNoise
from DBBand6Cart.WarmIFNoiseData import WarmIFNoiseData
from app.database.CTSDB import CTSDB
from DebugOptions import *
from ..Shared.MeasurementStatus import MeasurementStatus
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
            temperatureMonitor: TemperatureMonitor,
            measurementStatus: MeasurementStatus):
        
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.warmIFPlate = warmIFPlate
        self.powerMeter = powerMeter
        self.powerSupply = powerSupply
        self.temperatureMonitor = temperatureMonitor
        self.measurementStatus = measurementStatus
        self.database = WarmIFNoiseData(driver = CTSDB())
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers = 1)
        self.commonSettings = None
        self.settings = None
        self.finished = True
        self.rawData = []

    def reset(self):
        self.keyCartTest = 0
        self.stopNow = False
        self.finished = False
        self.rawData = []

    def updateSettings(self, commonSettings = None):
        if commonSettings is not None:
            self.commonSettings = commonSettings

    def start(self, keyCartTest: int):
        self.reset()
        self.keyCartTest = keyCartTest
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
        self.powerMeter.setUnits(Unit.W)
        self.warmIFPlate.outputSwitch.setValue(OutputSelect.POWER_METER, LoadSelect.THROUGH, PadSelect.PAD_OUT)
        self.warmIFPlate.inputSwitch.setValue(InputSelect.NOISE_DIODE)
        if self.stopNow:
            self.finished = True
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
                self.measurementStatus.setStatusMessage(f"Warm IF Noise: IF={freq:.2f} GHz, atten={atten} dB")
                self.warmIFPlate.attenuator.setValue(atten)
    
                if self.stopNow:
                    self.measurementStatus.setStatusMessage("User stop")
                    self.measurementStatus.setComplete(True)
                    self.finished = True
                    return

                self.powerSupply.setOutputEnable(True)
                time.sleep(0.25)
                pHot = self.powerMeter.autoRead()
                self.powerSupply.setOutputEnable(False)
                time.sleep(0.25)
                pCold = self.powerMeter.autoRead()
                ambient, err = self.temperatureMonitor.readSingle(self.commonSettings.sensorAmbient)
                record = WarmIFNoise(
                    fkCartTest = self.keyCartTest,
                    fkDUT_Type = DUT_Types.BAND6_CARTRIDGE,
                    freqYig = freq,
                    atten = atten,
                    pHot = pHot,
                    pCold = pCold,
                    tAmbient = ambient,
                    noiseDiodeENR = self.settings.diodeEnr
                )
                if not SIMULATE:
                    self.database.create(record)
                else:
                    record.id = int(freq * 100 + atten)                
                self.rawData.append(record)
        self.measurementStatus.setStatusMessage("Warm IF Noise: Done.")
        self.finished = True
