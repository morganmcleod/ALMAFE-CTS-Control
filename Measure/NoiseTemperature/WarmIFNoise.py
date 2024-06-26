from INSTR.WarmIFPlate.InputSwitch import InputSelect
from INSTR.WarmIFPlate.OutputSwitch import OutputSelect, LoadSelect, PadSelect
from INSTR.WarmIFPlate.WarmIFPlate import WarmIFPlate
from INSTR.WarmIFPlate.ExternalSwitch import ExternalSwitch, ExtInputSelect
from INSTR.PowerMeter.KeysightE441X import PowerMeter, Unit
from INSTR.PowerSupply.AgilentE363xA import PowerSupply
from INSTR.SpectrumAnalyzer.SpectrumAnalyzer import SpectrumAnalyzer
from INSTR.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from DBBand6Cart.schemas.WarmIFNoise import DUT_Types, WarmIFNoise
from DBBand6Cart.WarmIFNoiseData import WarmIFNoiseData
from app.database.CTSDB import CTSDB
from DebugOptions import *
from ..Shared.MeasurementStatus import MeasurementStatus
from .schemas import CommonSettings, WarmIFSettings, BackEndMode

import concurrent.futures
import logging
import time
import copy

class WarmIfNoise():

    def __init__(self, 
            warmIFPlate: WarmIFPlate, 
            powerMeter: PowerMeter,
            spectrumAnalyzer: SpectrumAnalyzer,
            powerSupply: PowerSupply,
            temperatureMonitor: TemperatureMonitor,
            measurementStatus: MeasurementStatus,
            externalSwitch: ExternalSwitch):
        
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.warmIFPlate = warmIFPlate
        self.externalSwitch = externalSwitch
        self.powerMeter = powerMeter
        self.spectrumAnalyzer = spectrumAnalyzer
        self.powerSupply = powerSupply
        self.temperatureMonitor = temperatureMonitor
        self.measurementStatus = measurementStatus
        self.database = WarmIFNoiseData(driver = CTSDB())
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers = 1)
        self.commonSettings = None
        self.ntSpecAnSettings = None
        self.settings = None
        self.finished = True
        self.rawData = []

    def reset(self):
        self.keyCartTest = 0
        self.stopNow = False
        self.finished = False
        self.rawData = []

    def updateSettings(self, 
            commonSettings = None,
            warmIFSettings = None,
            ntSpecAnSettings = None):
        if commonSettings is not None:
            self.commonSettings = commonSettings
        if warmIFSettings is not None:
            self.settings = warmIFSettings
        if ntSpecAnSettings is not None:
            self.ntSpecAnSettings = ntSpecAnSettings

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

        ifSteps = [
            self.settings.ifStart + i * self.settings.ifStep 
            for i in range(int((self.settings.ifStop - self.settings.ifStart) / self.settings.ifStep + 1))
        ]

        ### IF PLATE MODE ###
        if self.commonSettings.backEndMode == BackEndMode.IF_PLATE.value:
            attenSteps = [
                self.settings.attenStart + i * self.settings.attenStep 
                for i in range(int((self.settings.attenStop - self.settings.attenStart) / self.settings.attenStep + 1))
            ]            
            self.powerMeter.setUnits(Unit.W)            
            self.warmIFPlate.outputSwitch.setValue(OutputSelect.POWER_METER, LoadSelect.THROUGH, PadSelect.PAD_OUT)            
            self.warmIFPlate.inputSwitch.setValue(InputSelect.NOISE_DIODE)
            if self.stopNow:
                self.finished = True
                return
        
        
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

        ### SPECTRUM ANALYZER MODE ***
        elif self.commonSettings.backEndMode == BackEndMode.SPEC_AN.value:
            self.ntSpecAnSettings.sweepPoints = int((self.settings.ifStop - self.settings.ifStart) / self.settings.ifStep) + 1
            self.spectrumAnalyzer.configureAll(self.ntSpecAnSettings)
            self.spectrumAnalyzer.configFreqStartStop(self.settings.ifStart * 1e9, self.settings.ifStop * 1e9)

            self.externalSwitch.setValue(ExtInputSelect.NOISE_DIODE)

            self.powerSupply.setOutputEnable(True)
            time.sleep(0.25)
            success, msg = self.spectrumAnalyzer.readTrace()
            pHots = copy.copy(self.spectrumAnalyzer.traceY)
            self.powerSupply.setOutputEnable(False)
            time.sleep(0.25)
            success, msg = self.spectrumAnalyzer.readTrace()

            ambient, err = self.temperatureMonitor.readSingle(self.commonSettings.sensorAmbient)

            for freq, pHot, pCold in zip(ifSteps, pHots, self.spectrumAnalyzer.traceY):
                record = WarmIFNoise(
                    fkCartTest = self.keyCartTest,
                    fkDUT_Type = DUT_Types.BAND6_CARTRIDGE,
                    freqYig = freq,
                    atten = 0,
                    pHot = 10 ** (pHot / 10) / 1000,
                    pCold = 10 ** (pCold / 10) / 1000,
                    tAmbient = ambient,
                    noiseDiodeENR = self.settings.diodeEnr
                )                
                if not SIMULATE:
                    self.database.create(record)
                else:
                    record.id = int(freq)
                self.rawData.append(record)

        self.measurementStatus.setStatusMessage("Warm IF Noise: Done.")
        self.finished = True
