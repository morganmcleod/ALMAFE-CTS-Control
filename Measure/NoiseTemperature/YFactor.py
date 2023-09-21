from CTSDevices.PowerMeter.KeysightE441X import PowerMeter, Unit
from CTSDevices.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from CTSDevices.Chopper.Band6Chopper import Chopper, State
from .schemas import CommonSettings, YFactorDatum

from DebugOptions import *

import logging
import time
from statistics import mean

class YFactor():

    def __init__(self,
            powerMeter: PowerMeter,
            tempMonitor: TemperatureMonitor,
            chopper: Chopper,
            commonSettings: CommonSettings):
        
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.powerMeter = powerMeter
        self.tempMonitor = tempMonitor
        self.chopper = chopper
        self.commonSettings = commonSettings
        self.stopNow = False

    def start(self):
        self.stopNow = False
        self.rawData = []
        self.Y = 0
        self.TRx = 0
        self.__run()

    def stop(self):
        self.stopNow = True

    def __run(self) -> None:
        self.chopper.spin(self.commonSettings.chopperSpeed)
        self.powerMeter.setUnits(Unit.DBM)
        self.powerMeter.setFastMode(True)
        sampleInterval = 1 / self.commonSettings.sampleRate
        calcIter = self.commonSettings.powerMeterConfig.minS

        while not self.stopNow:
            cycleStart = time.time()
            cycleEnd = cycleStart + sampleInterval
            state = self.chopper.getState()
            power = self.powerMeter.read()
            self.rawData.append(YFactorDatum(chopperState = state, power = power))
            calcIter -= 1
            if calcIter == 0:
                self.__calculate()
                calcIter = self.commonSettings.powerMeterConfig.minS
            now = time.time()
            if now < cycleEnd:
                time.sleep(cycleEnd - now)

    def __calculate(self):
        N = self.commonSettings.powerMeterConfig.minS * 3
        if N > len(self.rawData):
            N = len(self.rawData)
        pHot = mean([x.power for x in self.rawData[:-N] if x.state == State.CLOSED])
        pCold = mean([x.power for x in self.rawData[:-N] if x.state == State.OPEN])
        self.Y = pHot - pCold
        Ylinear = 10 ^ (self.Y / 10)
        Tamb, _ = self.tempMonitor.readSingle(self.commonSettings.sensorAmbient)
        self.TRx = (Tamb - self.commonSettings.tColdEff * Ylinear) / (Ylinear - 1)
