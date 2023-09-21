from CTSDevices.WarmIFPlate.WarmIFPlate import WarmIFPlate
from CTSDevices.PowerMeter.KeysightE441X import PowerMeter
from CTSDevices.PowerSupply.AgilentE363xA import PowerSupply
from CTSDevices.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from CTSDevices.Chopper.Band6Chopper import Chopper
from CTSDevices.SignalGenerator.Keysight_PSG_MXG import SignalGenerator
from CTSDevices.FEMC.CartAssembly import CartAssembly
from AMB.LODevice import LODevice
from DBBand6Cart.CartTests import CartTest, CartTests
from DBBand6Cart.TestTypes import TestTypeIds
from app.database.CTSDB import CTSDB

from .WarmIFNoise import WarmIfNoise
from .NoiseTemperature import NoiseTemperature
from ..Shared.MeasurementStatus import MeasurementStatus
from DebugOptions import *

from .schemas import TestSteps

import concurrent.futures
import logging
import time

class NoiseTempMain():

    def __init__(self,
            loReference: SignalGenerator, 
            rfReference: SignalGenerator,
            cartAssembly: CartAssembly,
            rfSrcDevice: LODevice,
            warmIFPlate: WarmIFPlate, 
            powerMeter: PowerMeter,
            powerSupply: PowerSupply,
            temperatureMonitor: TemperatureMonitor,
            chopper: Chopper,
            measurementStatus: MeasurementStatus):
        
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.loReference = loReference
        self.rfReference = rfReference
        self.cartAssembly = cartAssembly
        self.rfSrcDevice = rfSrcDevice
        self.warmIFPlate = warmIFPlate
        self.powerMeter = powerMeter
        self.powerSupply = powerSupply
        self.temperatureMonitor = temperatureMonitor
        self.chopper = chopper
        self.measurementStatus = measurementStatus
        self.commonSettings = None
        self.warmIFSettings = None
        self.noiseTempSetings = None
        self.loWgIntegritySettings = None
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers = 1)
        self.warmIfNoise = WarmIfNoise(
            self.warmIFPlate,
            self.powerMeter,
            self.powerSupply,
            self.temperatureMonitor
        )
        self.noiseTemp = NoiseTemperature(
            self.loReference,
            self.rfReference,
            self.cartAssembly,
            self.rfSrcDevice,
            self.warmIFPlate,
            self.powerMeter,
            self.temperatureMonitor,
            self.chopper,
            self.measurementStatus
        )
        self.__reset()
        
    def __reset(self):
        self.testSteps = TestSteps()
        self.measInProgress = None
        self.stopNow = False
        
    def start(self, cartTest: CartTest) -> int:
        cartTestsDb = CartTests(driver = CTSDB())
        if SIMULATE:
            self.keyCartTest = 1
        else:
            # if we are measuring noise temperature then make that the master CartTests record
            if self.testSteps.noiseTemp:
                cartTest.fkTestType = TestTypeIds.NOISE_TEMP
                self.keyCartTest = cartTestsDb.create(cartTest)
            
            # if not noise temp but LO WG integrity, make that the master record:
            elif self.testSteps.loWGIntegrity:
                cartTest.fkTestType = TestTypeIds.LO_WG_INTEGRITY
                self.keyCartTest = cartTestsDb.create(cartTest)

            # if only measuring warm IF noise:
            elif self.testSteps.warmIF:
                cartTest.fkTestType = TestTypeIds.IF_PLATE_NOISE
                self.keyCartTest = cartTestsDb.create(cartTest)

        self.stopNow = False
        self.futures = []
        self.futures.append(self.executor.submit(self.__run))
        return self.keyCartTest

    def __run(self):
        if self.stopNow:
            self.logger.info("User stop")
            return
            
        if self.warmIFSettings and self.testSteps.warmIF:
            self.measInProgress = self.warmIfNoise
            self.warmIfNoise.settings = self.warmIFSettings
            self.warmIfNoise.commonSettings = self.commonSettings
            self.warmIfNoise.start()
            while self.warmIfNoise.isMeasuring():
                if self.stopNow:
                    self.logger.info("User stop")
                    return
                time.sleep(1)

        if self.stopNow:
            self.logger.info("User stop")
            return
        
        if self.noiseTempSetings and self.testSteps.noiseTemp:
            self.measInProgress = self.noiseTemp
            self.noiseTemp.settings = self.noiseTempSetings
            self.noiseTemp.commonSettings = self.commonSettings
            self.noiseTemp.start(doImageReject = self.testSteps.imageReject)
            while self.noiseTemp.isMeasuring():
                if self.stopNow:
                    self.logger.info("User stop")
                    return
                time.sleep(1)

        if self.stopNow:
            self.logger.info("User stop")
            return
        
        if self.loWgIntegritySettings and self.testSteps.loWGIntegrity:
            self.measInProgress = self.noiseTemp
            self.noiseTemp.settings = self.loWgIntegritySettings
            self.noiseTemp.commonSettings = self.commonSettings
            self.noiseTemp.start()
            while self.noiseTemp.isMeasuring():
                if self.stopNow:
                    self.logger.info("User stop")
                    return
                time.sleep(1)

        self.measInProgress = None

    def stop(self):
        if self.measInProgress:
            self.measInProgress.stop()
        if self.futures:
            concurrent.futures.wait(self.futures)
        self.measInProgress = None
        self.logger.info("NoiseTemperature: stopped")
