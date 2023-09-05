from CTSDevices.WarmIFPlate.WarmIFPlate import WarmIFPlate
from CTSDevices.PowerMeter.KeysightE441X import PowerMeter
from CTSDevices.PowerSupply.AgilentE363xA import PowerSupply
from CTSDevices.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from CTSDevices.Chopper.Band6Chopper import Chopper
from CTSDevices.SignalGenerator.Keysight_PSG_MXG import SignalGenerator
from CTSDevices.Cartridge.CartAssembly import CartAssembly
from AMB.LODevice import LODevice
from DBBand6Cart.CartTests import CartTest, CartTests
from DBBand6Cart.TestTypes import TestTypeIds
from app.database.CTSDB import CTSDB

from .MeasureWarmIFNoise import MeasureWarmIfNoise
from .MeasureNoiseTemperature import MeasureNoiseTemperature
from DebugOptions import *

from .schemas import WarmIFSettings, NoiseTempSettings, ImageRejectSettings, LoWGIntegritySettings

import concurrent.futures
import logging
import time

class NoiseTemperature():

    def __init__(self,
            loReference: SignalGenerator, 
            rfReference: SignalGenerator,
            cartAssembly: CartAssembly,
            rfSrcDevice: LODevice,
            warmIfPlate: WarmIFPlate, 
            powerMeter: PowerMeter,
            powerSupply: PowerSupply,
            tempMonitor: TemperatureMonitor,
            chopper: Chopper):
        
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.loReference = loReference
        self.rfReference = rfReference
        self.cartAssembly = cartAssembly
        self.rfSrcDevice = rfSrcDevice
        self.warmIFPlate = warmIfPlate
        self.powerMeter = powerMeter
        self.powerSupply = powerSupply
        self.tempMonitor = tempMonitor
        self.chopper = chopper
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers = 1)
        self.stopNow = False
        self.measInProgress = None
        
    def start(self,
            cartTest: CartTest,
            warmIFSettings: WarmIFSettings = None,
            noiseTempSetings: NoiseTempSettings = None,
            imageRejectSettings: ImageRejectSettings = None,
            loWgIntegritySettings: LoWGIntegritySettings = None) -> int:
                
        self.warmIFSettings = warmIFSettings
        self.noiseTempSetings = noiseTempSetings
        self.imageRejectSettings = imageRejectSettings
        self.loWgIntegritySettings = loWgIntegritySettings
        
        cartTestsDb = CartTests(driver = CTSDB())

        if SIMULATE:
            self.keyCartTest = 1
        else:
            # if we are measuring noise temperature then make that the master CartTests record
            if noiseTempSetings.enable:
                cartTest.fkTestType = TestTypeIds.NOISE_TEMP
                self.keyCartTest = cartTestsDb.create(cartTest)
            
            # if not noise temp but LO WG integrity, make that the master record:
            elif loWgIntegritySettings.enable:
                cartTest.fkTestType = TestTypeIds.LO_WG_INTEGRITY
                self.keyCartTest = cartTestsDb.create(cartTest)

            # if only measuring warm IF noise:
            elif warmIFSettings.enable:
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
            
        if self.warmIFSettings and self.warmIFSettings.get('enable', False):
            self.measInProgress = MeasureWarmIfNoise(
                self.warmIFPlate,
                self.powerMeter,
                self.powerSupply,
                self.tempMonitor,
                self.warmIFSettings
            )
            self.measInProgress.start()
            while not self.measInProgress.finished():
                if self.stopNow:
                    self.logger.info("User stop")
                    return
                time.sleep(1)

        if self.stopNow:
            self.logger.info("User stop")
            return
        
        if self.noiseTempSetings and self.noiseTempSetings.get('enable', False):
            self.measInProgress = MeasureNoiseTemperature(
                self.loReference,
                self.rfReference,
                self.cartAssembly,
                self.rfSrcDevice,
                self.warmIFPlate,
                self.powerMeter,
                self.tempMonitor,
                self.chopper,
                self.noiseTempSetings,
                self.imageRejectSettings
            )
            self.measInProgress.start()
            while not self.measInProgress.finished():
                if self.stopNow:
                    self.logger.info("User stop")
                    return
                time.sleep(1)

        if self.stopNow:
            self.logger.info("User stop")
            return
        
        if self.loWgIntegritySettings and self.loWgIntegritySettings.get('enable', False):
            self.measInProgress = MeasureNoiseTemperature(
                self.loReference,
                self.rfReference,
                self.cartAssembly,
                self.rfSrcDevice,
                self.warmIFPlate,
                self.powerMeter,
                self.powerSupply,
                self.tempMonitor,
                self.chopper,
                self.loWgIntegritySettings,
                None
            )
            self.measInProgress.start()
            while not self.measInProgress.finished():
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
        self.logger.info("NoiseTemperature: stopped")
