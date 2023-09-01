from CTSDevices.WarmIFPlate.WarmIFPlate import WarmIFPlate
from CTSDevices.PowerMeter.KeysightE441X import PowerMeter
from CTSDevices.PowerSupply.AgilentE363xA import PowerSupply
from CTSDevices.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from CTSDevices.Chopper.Band6Chopper import Chopper

from MeasureWarmIFNoise import MeasureWarmIfNoise

import concurrent.futures
import logging
import time

class NoiseTemperature():

    def __init__(self,
            warmIfPlate: WarmIFPlate, 
            powerMeter: PowerMeter,
            powerSupply: PowerSupply,
            tempMonitor: TemperatureMonitor,
            chopper: Chopper):
        
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.warmIFPlate = warmIfPlate
        self.powerMeter = powerMeter
        self.powerSupply = powerSupply
        self.tempMonitor = tempMonitor
        self.chopper = chopper
        self.stopNow = False
        self.measInProgress = None
        
    def start(self,
            warmIFSettings: dict = None,
            noiseTempSetings: dict = None,
            imageRejectSettings: dict = None,
            loWgIntegritySettings: dict = None):
        self.warmIFSettings = warmIFSettings if warmIFSettings is not None else {}
        self.noiseTempSetings = noiseTempSetings if noiseTempSetings is not None else {}
        self.imageRejectSettings = imageRejectSettings if imageRejectSettings is not None else {}
        self.loWgIntegritySettings = loWgIntegritySettings if loWgIntegritySettings is not None else {}
        self.stopNow = False
        self.futures = []
        self.futures.append(self.executor.submit(self.__run))

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
            self.measInProgress = MeasureNoiseTemp(
                self.warmIFPlate,
                self.powerMeter,
                self.tempMonitor,
                self.chopper,
                self.noiseTempSettings,
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
            self.measInProgress = MeasureLoWgIntegrity(
                self.warmIFPlate,
                self.powerMeter,
                self.tempMonitor,
                self.chopper,
                self.loWgIntegritySettings
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
