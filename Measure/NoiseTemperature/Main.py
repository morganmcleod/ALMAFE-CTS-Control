from CTSDevices.WarmIFPlate.WarmIFPlate import WarmIFPlate
from CTSDevices.PowerMeter.KeysightE441X import PowerMeter
from CTSDevices.SpectrumAnalyzer.SpectrumAnalyzer import SpectrumAnalyzer
from CTSDevices.PowerSupply.AgilentE363xA import PowerSupply
from CTSDevices.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from CTSDevices.Chopper.Band6Chopper import Chopper
from CTSDevices.SignalGenerator.Keysight_PSG_MXG import SignalGenerator
from CTSDevices.FEMC.CartAssembly import CartAssembly
from CTSDevices.ColdLoad.AMI1720 import AMI1720
from AMB.LODevice import LODevice
from DBBand6Cart.CartTests import CartTest, CartTests
from DBBand6Cart.TestTypes import TestTypeIds
from app.database.CTSDB import CTSDB

from .ZeroPowerMeter import ZeroPowerMeter
from .WarmIFNoise import WarmIfNoise
from .NoiseTemperature import NoiseTemperature
from ..Shared.MeasurementStatus import MeasurementStatus
from DebugOptions import *

from .schemas import TestSteps, CommonSettings, WarmIFSettings, NoiseTempSettings, SpectrumAnalyzerSettings

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
            spectrumAnalyzer: SpectrumAnalyzer,
            powerSupply: PowerSupply,
            temperatureMonitor: TemperatureMonitor,
            coldLoadController: AMI1720,
            chopper: Chopper,
            measurementStatus: MeasurementStatus):
        
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.loReference = loReference
        self.rfReference = rfReference
        self.cartAssembly = cartAssembly
        self.rfSrcDevice = rfSrcDevice
        self.warmIFPlate = warmIFPlate
        self.powerMeter = powerMeter
        self.spectrumAnalyzer = spectrumAnalyzer,
        self.powerSupply = powerSupply
        self.temperatureMonitor = temperatureMonitor
        self.coldLoadController = coldLoadController
        self.chopper = chopper
        self.measurementStatus = measurementStatus
        self.testSteps = TestSteps()
        self.commonSettings = CommonSettings()
        self.warmIFSettings = WarmIFSettings()
        self.noiseTempSetings = NoiseTempSettings()
        self.loWgIntegritySettings = NoiseTempSettings(loStep = 0.1, ifStart = 6.0, ifStop = 6.0)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers = 1)
        self.zeroPowerMeter = ZeroPowerMeter(
            self.warmIFPlate,
            self.powerMeter,
            self.measurementStatus
        )
        self.warmIfNoise = WarmIfNoise(
            self.warmIFPlate,
            self.powerMeter,
            self.powerSupply,
            self.temperatureMonitor,
            self.measurementStatus
        )
        self.warmIfNoise.updateSettings(self.commonSettings)
        self.noiseTemp = NoiseTemperature(
            self.loReference,
            self.rfReference,
            self.cartAssembly,
            self.rfSrcDevice,
            self.warmIFPlate,
            self.powerMeter,
            self.spectrumAnalyzer,
            self.temperatureMonitor,
            self.coldLoadController,
            self.chopper,
            self.measurementStatus
        )
        self.noiseTemp.updateSettings(self.commonSettings)
        self.__reset()
        
    def __reset(self):
        self.measInProgress = None
        self.stopNow = False
        
    def updateSettings(self, commonSettings = None, noiseTempSetings = None, warmIFSettings = None, loWgIntegritySettings = None):
        if commonSettings is not None:
            self.commonSettings = commonSettings
        if noiseTempSetings is not None:
            self.noiseTempSetings = noiseTempSetings
        if warmIFSettings is not None:
            self.warmIFSettings = warmIFSettings
        if loWgIntegritySettings is not None:
            self.loWgIntegritySettings = loWgIntegritySettings
        self.warmIfNoise.updateSettings(self.commonSettings)
        self.noiseTemp.updateSettings(self.commonSettings)

    def start(self, cartTest: CartTest) -> int:
        self.__reset()
        cartTestsDb = CartTests(driver = CTSDB())
        if SIMULATE:
            self.keyCartTest = 1
        else:
            # if we are measuring noise temperature then make that the master CartTests record
            if self.testSteps.noiseTemp:
                cartTest.fkTestType = TestTypeIds.NOISE_TEMP.value
            # if not noise temp but LO WG integrity, make that the master record:
            elif self.testSteps.loWGIntegrity:
                cartTest.fkTestType = TestTypeIds.LO_WG_INTEGRITY.value
            # if only measuring warm IF noise:
            elif self.testSteps.warmIF:
                cartTest.fkTestType = TestTypeIds.IF_PLATE_NOISE.value

            self.keyCartTest = cartTestsDb.create(cartTest)

        self.stopNow = False
        self.futures = []
        self.futures.append(self.executor.submit(self.__run))
        self.measurementStatus.setStatusMessage("Started")
        self.measurementStatus.setError(False)
        return self.keyCartTest

    def isMeasuring(self) -> bool:
        return self.warmIfNoise.isMeasuring() or self.noiseTemp.isMeasuring()

    def __run(self):
        self.measurementStatus.setComplete(False)
        try:
            if self.stopNow:
                self.logger.info("NoiseTempMain: User stop")
                return
                
            if self.testSteps.zeroPM:
                self.measInProgress = self.zeroPowerMeter
                self.zeroPowerMeter.start()
                while self.zeroPowerMeter.isMeasuring():
                    if self.stopNow:
                        self.logger.info("NoiseTempMain: User stop")                
                        return
                    time.sleep(1)
            
            if self.stopNow:
                self.logger.info("NoiseTempMain: User stop")                
                return
            
            if self.warmIFSettings and self.testSteps.warmIF:
                self.measInProgress = self.warmIfNoise
                self.warmIfNoise.settings = self.warmIFSettings
                self.warmIfNoise.commonSettings = self.commonSettings
                self.warmIfNoise.start(self.keyCartTest)
                while self.warmIfNoise.isMeasuring():
                    if self.stopNow:
                        self.logger.info("NoiseTempMain: User stop")                
                        return
                    time.sleep(1)

            if self.stopNow:
                self.logger.info("NoiseTempMain: User stop")                
                return
            
            if self.noiseTempSetings and self.testSteps.noiseTemp:
                self.measInProgress = self.noiseTemp
                self.noiseTemp.settings = self.noiseTempSetings
                self.noiseTemp.commonSettings = self.commonSettings
                self.noiseTemp.start(self.keyCartTest, doImageReject = self.testSteps.imageReject)
                while self.noiseTemp.isMeasuring():
                    if self.stopNow:
                        self.logger.info("NoiseTempMain: User stop")                
                        return
                    time.sleep(1)

            if self.stopNow:
                self.logger.info("NoiseTempMain: User stop")                
                return
            
            if self.loWgIntegritySettings and self.testSteps.loWGIntegrity:
                self.measInProgress = self.noiseTemp
                self.noiseTemp.settings = self.loWgIntegritySettings
                self.noiseTemp.commonSettings = self.commonSettings
                self.noiseTemp.start()
                while self.noiseTemp.isMeasuring():
                    if self.stopNow:
                        self.logger.info("NoiseTempMain: User stop")                
                        return
                    time.sleep(1)
        
        except Exception as e:
            self.logger.error("NoiseTempMain.__run")
            self.logger.error(e)

        self.measurementStatus.setComplete(True)
        self.measurementStatus.setMeasuring(None)
        self.measInProgress = None

    def stop(self):
        self.measurementStatus.setStatusMessage("Stopping...")
        self.stopNow = True
        if self.measInProgress:
            self.measInProgress.stop()
        if self.futures:
            concurrent.futures.wait(self.futures)
        self.measInProgress = None
        self.measurementStatus.setComplete(True)
        self.logger.info("NoiseTempMain: stopped")

    def cleanup(self):
        self.noiseTemp.cleanup()
