
from INSTR.WarmIFPlate.InputSwitch import InputSelect
from INSTR.WarmIFPlate.OutputSwitch import OutputSelect, LoadSelect, PadSelect
from INSTR.PowerMeter.KeysightE441X import PowerMeter, Unit
from INSTR.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from INSTR.WarmIFPlate.WarmIFPlate import WarmIFPlate
from INSTR.Chopper.Band6Chopper import Chopper, State
from .schemas import CommonSettings, ChopperPowers, YFactorSample
from ..Shared.MeasurementStatus import MeasurementStatus
import concurrent.futures
from DebugOptions import *

import logging
import time
from statistics import mean

class YFactor():

    def __init__(self,
            warmIFPlate: WarmIFPlate, 
            powerMeter: PowerMeter,
            tempMonitor: TemperatureMonitor,
            chopper: Chopper,
            commonSettings: CommonSettings,
            measurementStatus: MeasurementStatus):
        
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.warmIFPlate = warmIFPlate
        self.powerMeter = powerMeter
        self.tempMonitor = tempMonitor
        self.chopper = chopper
        self.commonSettings = commonSettings
        self.measurementStatus = measurementStatus
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers = 1)
        self.yFactorHistory = []
        self.stopNow = False
        self.finished = True

    def start(self):
        self.stopNow = False
        self.finished = False
        self.rawData = []
        self.yFactorHistory = []
        self.futures = []
        self.futures.append(self.executor.submit(self.__run))
        self.measurementStatus.setStatusMessage("Y-factor started")
        self.measurementStatus.setError(False)

    def stop(self):
        self.stopNow = True
    
    def isMeasuring(self):
        return not self.finished    

    def __run(self) -> None:
        self.measurementStatus.setComplete(False)
        self.chopper.spin(self.commonSettings.chopperSpeed)
        self.powerMeter.setUnits(Unit.DBM)
        self.powerMeter.setFastMode(False)
        self.warmIFPlate.outputSwitch.setValue(OutputSelect.POWER_METER, LoadSelect.THROUGH, PadSelect.PAD_OUT)
        self.warmIFPlate.inputSwitch.setValue(InputSelect.POL0_USB)
        self.warmIFPlate.yigFilter.setFrequency(6.0)
        self.warmIFPlate.attenuator.setValue(22.0)

        sampleInterval = 1 / self.commonSettings.sampleRate
        calcIter = self.commonSettings.powerMeterConfig.minS
        retainSamples = calcIter * 2

        while not self.stopNow:
            cycleStart = time.time()
            cycleEnd = cycleStart + sampleInterval
            state = self.chopper.getState()
            power = self.powerMeter.read()
            self.rawData.append(ChopperPowers(input="POL0 USB", chopperState = state, power = power))
            calcIter -= 1
            if calcIter == 0:
                self.__calculate(retainSamples)
                calcIter = self.commonSettings.powerMeterConfig.minS
            now = time.time()
            if now < cycleEnd:
                time.sleep(cycleEnd - now)
            else:
                if len(self.rawData) > retainSamples:
                    self.rawData = self.rawData[-retainSamples:]
        
        self.chopper.stop()
        self.chopper.gotoHot()
        self.measurementStatus.setStatusMessage("Y-factor stopped")
        self.measurementStatus.setComplete(True)
        self.finished = True

    def __calculate(self, retainSamples: int):
        N = self.commonSettings.powerMeterConfig.minS * 3
        if N > len(self.rawData):
            N = len(self.rawData)
        pHot = [x.power for x in self.rawData[-N:] if x.chopperState == State.OPEN]
        pCold = [x.power for x in self.rawData[-N:] if x.chopperState == State.CLOSED]
        if len(pHot) < 2 or len(pCold) < 2:
            return
        pHot = mean(pHot)
        pCold = mean(pCold)
        Y = pHot - pCold
        Ylinear = 10 ** (Y / 10)
        tAmb, tErr = self.tempMonitor.readSingle(self.commonSettings.sensorAmbient)
        if tErr or tAmb < 1:
            return
        TRx = (tAmb - self.commonSettings.tColdEff * Ylinear) / (Ylinear - 1)
        self.yFactorHistory.append(YFactorSample(Y = Y, TRx = TRx))
        if len(self.yFactorHistory) > retainSamples:
            self.yFactorHistory = self.yFactorHistory[-retainSamples:]
