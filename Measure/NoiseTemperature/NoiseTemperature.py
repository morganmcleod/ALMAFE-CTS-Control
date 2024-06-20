from CTSDevices.WarmIFPlate.WarmIFPlate import WarmIFPlate
from CTSDevices.WarmIFPlate.InputSwitch import InputSelect
from CTSDevices.WarmIFPlate.OutputSwitch import OutputSelect, LoadSelect, PadSelect
from CTSDevices.WarmIFPlate.ExternalSwitch import ExternalSwitch, ExtInputSelect
from CTSDevices.PowerMeter.KeysightE441X import PowerMeter, Unit
from CTSDevices.SpectrumAnalyzer.SpectrumAnalyzer import SpectrumAnalyzer
from CTSDevices.SpectrumAnalyzer.schemas import SpectrumAnalyzerSettings
from CTSDevices.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from CTSDevices.Chopper.Band6Chopper import Chopper, State
from CTSDevices.SignalGenerator.Keysight_PSG_MXG import SignalGenerator
from CTSDevices.FEMC.CartAssembly import CartAssembly
from CTSDevices.FEMC.RFSource import RFSource
from CTSDevices.ColdLoad.AMI1720 import AMI1720
from CTSDevices.Common.BinarySearchController import BinarySearchController
from DBBand6Cart.schemas.NoiseTempRawDatum import NoiseTempRawDatum
from DBBand6Cart.NoiseTempRawData import NoiseTempRawData
from app.database.CTSDB import CTSDB
from ..Shared.makeSteps import makeSteps
from ..Shared.MeasurementStatus import MeasurementStatus
from .schemas import ChopperPowers, BackEndMode, SelectPolarization, SpecAnPowers, TestSteps

from DebugOptions import *

import concurrent.futures
import logging
import time
from datetime import datetime
from statistics import mean, stdev
from math import sqrt, log10
import copy

class NoiseTemperature():

    def __init__(self,
            loReference: SignalGenerator,
            rfReference: SignalGenerator,
            cartAssembly: CartAssembly,
            rfSrcDevice: RFSource,
            warmIFPlate: WarmIFPlate,
            powerMeter: PowerMeter,
            spectrumAnalyzer: SpectrumAnalyzer,
            tempMonitor: TemperatureMonitor,
            coldLoadController: AMI1720,
            chopper: Chopper,
            measurementStatus: MeasurementStatus,
            externalSwitch: ExternalSwitch):
        
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.loReference = loReference
        self.rfReference = rfReference
        self.cartAssembly = cartAssembly
        self.rfSrcDevice = rfSrcDevice        
        self.warmIFPlate = warmIFPlate
        self.externalSwitch = externalSwitch
        self.powerMeter = powerMeter
        self.spectrumAnalyzer = spectrumAnalyzer
        self.tempMonitor = tempMonitor
        self.coldLoadController = coldLoadController
        self.chopper = chopper
        self.measurementStatus = measurementStatus
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers = 1)
        self.commonSettings = None
        self.settings = None
        self.ntSpecAnSettings = None
        self.irSpecAnSettings = None
        self.__reset()        

    def __reset(self):
        self.ntRawData = NoiseTempRawData(driver = CTSDB())
        self.keyCartTest = 0
        self.stopNow = False
        self.finished = False
        self.ifAtten = 22
        self.chopperPowerHistory = []
        self.specAnPowerHistory = None
        self.rawDataRecords = None
        self.currentRecords = [None, None]
        self.loStep = 0
        self.ifStep = 0
        
    def updateSettings(self, 
            commonSettings = None, 
            noiseTempSettings = None,
            ntSpecAnSettings = None,
            irSpecAnSettings = None):
        if commonSettings is not None:
            self.commonSettings = commonSettings
        if noiseTempSettings is not None:
            self.settings = noiseTempSettings
        if ntSpecAnSettings is not None:
            self.ntSpecAnSettings = ntSpecAnSettings
        if irSpecAnSettings is not None:
            self.irSpecAnSettings = irSpecAnSettings

    def start(self, keyCartTest: int, testSteps: TestSteps, automated: bool = True):
        self.__reset()
        self.keyCartTest = keyCartTest
        self.testSteps = testSteps
        self.selectPol = SelectPolarization(self.settings.polarization)
        self.loSteps = makeSteps(self.settings.loStart, self.settings.loStop, self.settings.loStep)
        self.ifSteps = makeSteps(self.settings.ifStart, self.settings.ifStop, self.settings.ifStep)
                
        self.chopper.stop()
        self.coldLoadController.startFill()
        if self.commonSettings.backEndMode == BackEndMode.IF_PLATE.value:
            self.powerMeter.setUnits(Unit.DBM)
            self.powerMeter.setFastMode(False)
            self.warmIFPlate.outputSwitch.setValue(OutputSelect.POWER_METER, LoadSelect.THROUGH, PadSelect.PAD_OUT)
            self.warmIFPlate.inputSwitch.setValue(InputSelect.POL0_USB)
            self.warmIFPlate.yigFilter.setFrequency(self.settings.ifStart)
            self.warmIFPlate.attenuator.setValue(22.0)
        elif self.commonSettings.backEndMode == BackEndMode.SPEC_AN.value:
            self.spectrumAnalyzer.reset()            
        self.__rfSourceOff()
        if automated:
            self.futures = []
            self.futures.append(self.executor.submit(self.__run))
            concurrent.futures.wait(self.futures)
            self.cleanup()

    def cleanup(self):
        self.coldLoadController.stopFill()
        self.chopper.stop()
        self.__rfSourceOff()
        self.powerMeter.setUnits(Unit.DBM)
        self.powerMeter.setFastMode(False)

    def stop(self):
        self.stopNow = True

    def isMeasuring(self):
        return not self.finished
   
    def __run(self) -> None:        
        for freqLO in self.loSteps:
            if self.stopNow:
                self.finished = True
                self.measurementStatus.setStatusMessage("User stop")
                self.logger.info("User stop")
                return

            loLocked, msg = self.setLO(freqLO)
            if not loLocked:
                self.logger.error(msg)
            elif msg:
                self.logger.info(msg)

            ### IF PLATE MODE ###
            if self.commonSettings.backEndMode == BackEndMode.IF_PLATE.value:
                for freqIF in self.ifSteps:
                    success, msg = self.setIF(freqIF)

                    success, msg = self.checkColdLoad()
                    if not success:
                        self.logger.error(msg)
                    elif msg:
                        self.logger.info(msg)

                    if self.stopNow:
                        self.finished = True                
                        self.logger.info("User stop")
                        self.measurementStatus.setStatusMessage("User stop")
                        return                
                        
                    self.__initRawData(freqLO, freqIF, loLocked)
                        
                    if self.testSteps.imageReject:
                        success, msg = self.measureImageReject(freqLO, freqIF)
                        if not success:
                            self.logger.error(msg)
                        elif msg:
                            self.logger.info(msg)
                    
                    if self.stopNow:
                        self.finished = True                
                        self.logger.info("User stop")
                        self.measurementStatus.setStatusMessage("User stop")
                        return

                    if self.testSteps.noiseTemp:
                        success, msg = self.measureNoiseTemp(freqLO, freqIF)
                        if not success:
                            self.logger.error(msg)
                        elif msg:
                            self.logger.info(msg)

                    self.ntRawData.create(list(self.rawDataRecords.values()))
                    self.rawDataRecords = None

                    if self.stopNow:
                        self.finished = True                
                        self.logger.info("User stop")
                        self.measurementStatus.setStatusMessage("User stop")
                        return
            
            ### SPECTRUM ANALYZER MODE ***
            elif self.commonSettings.backEndMode == BackEndMode.SPEC_AN.value:
                success, msg = self.checkColdLoad()
                if not success:
                    self.logger.error(msg)
                elif msg:
                    self.logger.info(msg)

                if self.stopNow:
                    self.finished = True                
                    self.logger.info("User stop")
                    self.measurementStatus.setStatusMessage("User stop")
                    return                
                    
                self.__initRawData(freqLO, None, loLocked)
                    
                if self.testSteps.imageReject:
                    success, msg = self.measureImageReject(freqLO, freqIF = None)
                    if not success:
                        self.logger.error(msg)
                    elif msg:
                        self.logger.info(msg)
                
                if self.stopNow:
                    self.finished = True                
                    self.logger.info("User stop")
                    self.measurementStatus.setStatusMessage("User stop")
                    return

                if self.testSteps.noiseTemp:
                    success, msg = self.measureNoiseTemp(freqLO, freqIF = None)
                    if not success:
                        self.logger.error(msg)
                    elif msg:
                        self.logger.info(msg)

                self.ntRawData.create(list(self.rawDataRecords.values()))
                self.rawDataRecords = None

                if self.stopNow:
                    self.finished = True                
                    self.logger.info("User stop")
                    self.measurementStatus.setStatusMessage("User stop")
                    return
        
        self.measurementStatus.setStatusMessage("Noise Temperature: Done.")
        self.finished = True

    def __initRawData(self, freqLO: float, freqIF: float | None, loLocked: bool) -> tuple[bool, str]:
        if self.rawDataRecords:
            return False, "Raw data records already exist."
        
        try:
            tAmb, tErr = self.tempMonitor.readSingle(self.commonSettings.sensorAmbient)
        except:
            tAmb = 0

        try:
            cartridgeTemps = self.cartAssembly.ccaDevice.getCartridgeTemps()
        except:
            cartridgeTemps = None

        pll = self.cartAssembly.loDevice.getPLL()
        lockInfo = self.cartAssembly.loDevice.getLockInfo() #redundant
        pa = self.cartAssembly.loDevice.getPA()

        now = datetime.now()
        self.rawDataRecords = {}

        ### IF PLATE MODE ###
        if self.commonSettings.backEndMode == BackEndMode.IF_PLATE.value:
            
            if self.selectPol.testPol(0):
                sis01 = self.cartAssembly.ccaDevice.getSIS(pol = 0, sis = 1, averaging = 8)
                sis02 = self.cartAssembly.ccaDevice.getSIS(pol = 0, sis = 2, averaging = 8)

                self.rawDataRecords[(freqLO, freqIF, 0)] = NoiseTempRawDatum(
                    fkCartTest = self.keyCartTest,
                    timeStamp = now,
                    FreqLO = freqLO,
                    CenterIF = freqIF,
                    BWIF = 100,
                    Pol = 0,
                    TRF_Hot = tAmb,
                    IF_Attn = self.ifAtten, 
                    TColdLoad = self.commonSettings.tColdEff,
                    Vj1 = sis01['Vj'],
                    Ij1 = sis01['Ij'],
                    Imag = sis01['Imag'],
                    Vj2 = sis02['Vj'],
                    Ij2 = sis02['Ij'],
                    Tmixer = cartridgeTemps['temp2'] if cartridgeTemps else -1,
                    PLL_Lock_V = lockInfo['lockVoltage'],
                    PLL_Corr_V = lockInfo['corrV'],
                    PLL_Assm_T = pll['temperature'],
                    PA_A_Drain_V = pa['VDp0'],
                    PA_B_Drain_V = pa['VDp1'],
                    Is_LO_Unlocked = not loLocked
                )
            
            if self.selectPol.testPol(1):
                sis11 = self.cartAssembly.ccaDevice.getSIS(pol = 1, sis = 1, averaging = 8)
                sis12 = self.cartAssembly.ccaDevice.getSIS(pol = 1, sis = 2, averaging = 8)

                self.rawDataRecords[(freqLO, freqIF, 1)] = NoiseTempRawDatum(
                    fkCartTest = self.keyCartTest,
                    timeStamp = now,
                    FreqLO = freqLO,
                    CenterIF = freqIF,
                    BWIF = 100,
                    Pol = 1,
                    TRF_Hot = tAmb,
                    IF_Attn = self.ifAtten, 
                    TColdLoad = self.commonSettings.tColdEff,
                    Vj1 = sis11['Vj'],
                    Ij1 = sis11['Ij'],
                    Imag = sis11['Imag'],
                    Vj2 = sis12['Vj'],
                    Ij2 = sis12['Ij'],
                    Tmixer = cartridgeTemps['temp5'] if cartridgeTemps else -1,
                    PLL_Lock_V = lockInfo['lockVoltage'],
                    PLL_Corr_V = lockInfo['corrV'],
                    PLL_Assm_T = pll['temperature'],
                    PA_A_Drain_V = pa['VDp0'],
                    PA_B_Drain_V = pa['VDp1'],
                    Is_LO_Unlocked = not loLocked
                )
        
        ### SPECTRUM ANALYZER MODE ***
        elif self.commonSettings.backEndMode == BackEndMode.SPEC_AN.value:
            if self.selectPol.testPol(0):
                sis01 = self.cartAssembly.ccaDevice.getSIS(pol = 0, sis = 1, averaging = 8)
                sis02 = self.cartAssembly.ccaDevice.getSIS(pol = 0, sis = 2, averaging = 8)
            if self.selectPol.testPol(1):
                sis11 = self.cartAssembly.ccaDevice.getSIS(pol = 1, sis = 1, averaging = 8)
                sis12 = self.cartAssembly.ccaDevice.getSIS(pol = 1, sis = 2, averaging = 8)

            for freqIF in self.ifSteps:
                if self.selectPol.testPol(0):
                    self.rawDataRecords[(freqLO, freqIF, 0)] = NoiseTempRawDatum(
                        fkCartTest = self.keyCartTest,
                        timeStamp = now,
                        FreqLO = freqLO,
                        CenterIF = freqIF,
                        BWIF = 100,
                        Pol = 0,
                        TRF_Hot = tAmb,
                        IF_Attn = 0, 
                        TColdLoad = self.commonSettings.tColdEff,
                        Vj1 = sis01['Vj'],
                        Ij1 = sis01['Ij'],
                        Imag = sis01['Imag'],
                        Vj2 = sis02['Vj'],
                        Ij2 = sis02['Ij'],
                        Tmixer = cartridgeTemps['temp2'] if cartridgeTemps else -1,
                        PLL_Lock_V = lockInfo['lockVoltage'],
                        PLL_Corr_V = lockInfo['corrV'],
                        PLL_Assm_T = pll['temperature'],
                        PA_A_Drain_V = pa['VDp0'],
                        PA_B_Drain_V = pa['VDp1'],
                        Is_LO_Unlocked = not loLocked
                    )
                
                if self.selectPol.testPol(1):
                    self.rawDataRecords[(freqLO, freqIF, 1)] = NoiseTempRawDatum(
                        fkCartTest = self.keyCartTest,
                        timeStamp = now,
                        FreqLO = freqLO,
                        CenterIF = freqIF,
                        BWIF = 100,
                        Pol = 1,
                        TRF_Hot = tAmb,
                        IF_Attn = 0, 
                        TColdLoad = self.commonSettings.tColdEff,
                        Vj1 = sis11['Vj'],
                        Ij1 = sis11['Ij'],
                        Imag = sis11['Imag'],
                        Vj2 = sis12['Vj'],
                        Ij2 = sis12['Ij'],
                        Tmixer = cartridgeTemps['temp5'] if cartridgeTemps else -1,
                        PLL_Lock_V = lockInfo['lockVoltage'],
                        PLL_Corr_V = lockInfo['corrV'],
                        PLL_Assm_T = pll['temperature'],
                        PA_A_Drain_V = pa['VDp0'],
                        PA_B_Drain_V = pa['VDp1'],
                        Is_LO_Unlocked = not loLocked
                    )
        return True, ""

    def setLO(self, freqLO: float = 0, step: str = None, setBias: bool = True) -> tuple[bool, str]:
        if step == 'first':
            self.loStep = 0
            freqLO = self.loSteps[0]
        elif step == 'next':
            self.loStep += 1
            try:
                freqLO = self.loSteps[self.loStep]
            except:
                return False, "setLO: past last LO step"
        elif freqLO == 0:
            return False, "setLO: specify freqLO or step = 'first' or 'next'"

        self.measurementStatus.setStatusMessage(f"Locking LO at {freqLO:.2f} GHz...")
        success, msg = self.cartAssembly.lockLO(self.loReference, freqLO)

        locked = success        
        if not success:
            self.logger.error(msg)
        elif msg:
            self.logger.info(msg)

        if setBias:
            success = self.cartAssembly.setRecevierBias(freqLO)
            if not success:
                return False, "cartAssembly.setRecevierBias failed. Provide config ID?"
            
            self.measurementStatus.setStatusMessage(f"Setting LO power...")
            success = self.cartAssembly.setAutoLOPower(self.selectPol.testPol(0), self.selectPol.testPol(1))
            if not success:
                return False, "cartAssembly.setAutoLOPower failed"

        if locked:
            return True, f"Locked LO {'and set bias ' if setBias else ''}at {freqLO:.2f} GHz."
        else:
            return True, f"LO LOCK FAILED {'and set bias ' if setBias else ''}at {freqLO:.2f} GHz."

    def setIF(self, freqIF: float = 0, step: str = None, attenuatorAutoLevel: bool = True) -> tuple[bool, str]:

        if self.commonSettings.backEndMode == BackEndMode.SPEC_AN.value:
            raise ValueError("NoiseTemperature.setIF not allowed in BackEndMode.SPEC_AN")

        if step == 'first':
            self.ifStep = 0
            freqIF = self.ifSteps[0]
        elif step == 'next':
            self.ifStep += 1
            try:
                freqIF = self.ifSteps[self.ifStep]
            except:
                return False, "setIF: past last IF step"
        elif freqIF == 0:
            return False, "setIF: specify freqIF or step = 'first' or 'next'"
        
        if self.commonSettings.backEndMode == BackEndMode.IF_PLATE.value:
            self.warmIFPlate.yigFilter.setFrequency(freqIF)

        success, msg = (True, "")
        if attenuatorAutoLevel:
            success, msg = self.__attenuatorAutoLevel()
        
        if not success:
            self.logger.error(msg)
        elif msg:
            self.logger.info(msg)
        return success, msg

    def measureImageReject(self, freqLO: float, freqIF: float | None) -> tuple[bool, str]:

        self.chopper.gotoHot()

        ### IF PLATE MODE ###
        if self.commonSettings.backEndMode == BackEndMode.IF_PLATE.value:

            if freqIF is None:
                raise ValueError("NoiseTemperature.measureImageReject freqIF missing in IF_PLATE mode")

            self.measurementStatus.setStatusMessage(f"Measure image rejection LO={freqLO:.2f} GHz, IF={freqIF:.2f} GHz...")
            self.powerMeter.setUnits(Unit.DBM)
            self.powerMeter.setFastMode(False)

            for pol in (0, 1):
                if self.selectPol.testPol(pol):
                    if self.stopNow:
                        self.finished = True                
                        return True, "User stop"
                    
                    self.currentRecords[pol] = record = self.rawDataRecords[(freqLO, freqIF, pol)]
                    self.measurementStatus.setStatusMessage(f"Locking RF source at {freqLO + freqIF:.2f} GHz...")
                    rfLocked, msg = self.rfSrcDevice.lockRF(self.rfReference, freqLO + freqIF, self.commonSettings.sigGenAmplitude)
                    if rfLocked:
                        record.Is_RF_Unlocked = False
                        self.warmIFPlate.inputSwitch.setPolAndSideband(pol, 'USB')
                        time.sleep(0.25)                
                        success, msg = self.__rfSourceAutoLevel(freqIF)
                        record.Source_Power_USB = self.rfSrcDevice.getPAVD()
                        record.PwrUSB_SrcUSB = self.powerMeter.read()
                        self.warmIFPlate.inputSwitch.setPolAndSideband(pol, 'LSB')
                        time.sleep(0.25)                
                        record.PwrLSB_SrcUSB = self.powerMeter.read()
                    else:
                        record.Is_RF_Unlocked = True
                        record.PwrUSB_SrcUSB = -100
                        record.PwrLSB_SrcUSB = -200
                    if msg:
                        self.logger.info(msg)

                    if self.stopNow:
                        self.finished = True                
                        return True, "User stop"      
                    
                    self.measurementStatus.setStatusMessage(f"Locking RF source at {freqLO - freqIF:.2f} GHz...")
                    rfLocked, msg = self.rfSrcDevice.lockRF(self.rfReference, freqLO - freqIF, self.commonSettings.sigGenAmplitude)
                    if rfLocked:
                        record.Is_RF_Unlocked = False
                        self.warmIFPlate.inputSwitch.setPolAndSideband(pol, 'LSB')
                        time.sleep(0.25)                
                        success, msg = self.__rfSourceAutoLevel(freqIF)
                        record.Source_Power_LSB = self.rfSrcDevice.getPAVD()
                        record.PwrLSB_SrcLSB = self.powerMeter.read()
                        self.warmIFPlate.inputSwitch.setPolAndSideband(pol, 'USB')
                        time.sleep(0.25)                
                        record.PwrUSB_SrcLSB = self.powerMeter.read()
                    else:
                        record.Is_RF_Unlocked = True
                        record.PwrLSB_SrcLSB = -100
                        record.PwrUSB_SrcLSB = -200
                    if msg:
                        self.logger.info(msg)
                        
                self.__rfSourceOff()
        
        ### SPECTRUM ANALYZER MODE ###
        if self.commonSettings.backEndMode == BackEndMode.SPEC_AN.value:            
            self.spectrumAnalyzer.configureAll(self.irSpecAnSettings)            
            for freqIF in self.ifSteps:
                for pol in (0, 1):
                    if self.selectPol.testPol(pol):
            
                        if self.stopNow:
                            self.finished = True                
                            return True, "User stop"
                    
                        self.currentRecords[pol] = record = self.rawDataRecords[(freqLO, freqIF, pol)]

                        self.measurementStatus.setStatusMessage(f"Locking RF source at {freqLO + freqIF:.2f} GHz...")
                        rfLocked, msg = self.rfSrcDevice.lockRF(self.rfReference, freqLO + freqIF, self.commonSettings.sigGenAmplitude)
                        if rfLocked:
                            record.Is_RF_Unlocked = False
                            self.externalSwitch.setPolAndSideband(pol, 'USB')
                            self.spectrumAnalyzer.configNarrowBand(freqIF, 0.0001)
                            time.sleep(0.25)                
                            success, msg = self.__rfSourceAutoLevel(freqIF)
                            record.Source_Power_USB = self.rfSrcDevice.getPAVD()
                            success, msg = self.spectrumAnalyzer.measureNarrowBand()
                            record.PwrUSB_SrcUSB = self.spectrumAnalyzer.markerY
                            self.externalSwitch.setPolAndSideband(pol, 'LSB')
                            time.sleep(0.25)
                            success, msg = self.spectrumAnalyzer.measureNarrowBand()
                            record.Source_Power_LSB = self.rfSrcDevice.getPAVD()
                            record.PwrLSB_SrcUSB = self.spectrumAnalyzer.markerY
                        else:
                            record.Is_RF_Unlocked = True
                            record.PwrUSB_SrcUSB = -100
                            record.PwrLSB_SrcUSB = -200
                        if msg:
                            self.logger.info(msg)

                        if self.stopNow:
                            self.finished = True                
                            return True, "User stop"      
                        
                        self.measurementStatus.setStatusMessage(f"Locking RF source at {freqLO - freqIF:.2f} GHz...")
                        rfLocked, msg = self.rfSrcDevice.lockRF(self.rfReference, freqLO - freqIF, self.commonSettings.sigGenAmplitude)
                        if rfLocked:
                            record.Is_RF_Unlocked = False
                            self.externalSwitch.setPolAndSideband(pol, 'LSB')                            
                            time.sleep(0.25)                
                            success, msg = self.__rfSourceAutoLevel(freqIF)
                            success, msg = self.spectrumAnalyzer.measureNarrowBand()
                            record.PwrLSB_SrcLSB = self.spectrumAnalyzer.markerY
                            self.externalSwitch.setPolAndSideband(pol, 'USB')
                            time.sleep(0.25)
                            success, msg = self.spectrumAnalyzer.measureNarrowBand()                
                            record.PwrUSB_SrcLSB = self.spectrumAnalyzer.markerY
                        else:
                            record.Is_RF_Unlocked = True
                            record.PwrLSB_SrcLSB = -100
                            record.PwrUSB_SrcLSB = -200
                        if msg:
                            self.logger.info(msg)

                    self.__rfSourceOff()
                self.spectrumAnalyzer.endNarrowBand()        
        return True, ""
    
    def measureNoiseTemp(self, freqLO: float, freqIF: float | None) -> tuple[bool, str]:

        ### IF PLATE MODE ###
        if self.commonSettings.backEndMode == BackEndMode.IF_PLATE.value:

            if freqIF is None:
                raise ValueError("NoiseTemperature.measureImageReject freqIF missing in IF_PLATE mode")

            self.measurementStatus.setStatusMessage(f"Measure noise temperature LO={freqLO:.2f} GHz, IF={freqIF:.2f} GHz...")
        
            self.__rfSourceOff()
            self.powerMeter.setUnits(Unit.W)
            self.powerMeter.setFastMode(True)
            self.chopper.spin(self.commonSettings.chopperSpeed)
            self.warmIFPlate.yigFilter.setFrequency(freqIF)

            for pol in 0, 1:
                if self.selectPol.testPol(pol):
                    for sideband in ('USB', 'LSB'):
                        if self.stopNow:
                            self.finished = True
                            return True, "User stop"

                        success, msg = self.__measureNoiseTempSpin(freqLO, freqIF, pol, sideband)
                        if not success:
                            self.logger.error(msg)
        
        ### SPEC AN MODE ###
        if self.commonSettings.backEndMode == BackEndMode.SPEC_AN.value:
            self.measurementStatus.setStatusMessage(f"Measure noise temperature LO={freqLO:.2f} GHz...")

            self.chopper.stop()
            self.__rfSourceOff()
            self.ntSpecAnSettings.sweepPoints = int((self.settings.ifStop - self.settings.ifStart) / self.settings.ifStep) + 1
            self.spectrumAnalyzer.configureAll(self.ntSpecAnSettings)
            self.spectrumAnalyzer.configFreqStartStop(self.settings.ifStart * 1e9, self.settings.ifStop * 1e9)

            for pol in 0, 1:
                if self.selectPol.testPol(pol):
                    if self.stopNow:
                        self.finished = True
                        return True, "User stop"
                    
                    #select the IF record to be displayed to the user:
                    self.currentRecords[pol] = self.rawDataRecords[(freqLO, 6, pol)]
                    self.chopper.gotoHot()

                    #prepare the traces to be displayed to the user:
                    self.specAnPowerHistory = SpecAnPowers(pol = pol)

                    self.externalSwitch.setPolAndSideband(pol, 'USB')                        
                    success, msg = self.spectrumAnalyzer.readTrace()
                    if not success:
                        return False, msg

                    self.specAnPowerHistory.pHotUSB = self.spectrumAnalyzer.traceY
                    for freqIF, amp in zip(self.ifSteps, self.spectrumAnalyzer.traceY):
                        record = self.rawDataRecords[(freqLO, freqIF, pol)]
                        record.Phot_USB = amp

                    self.externalSwitch.setPolAndSideband(pol, 'LSB')
                    success, msg = self.spectrumAnalyzer.readTrace()
                    if not success:
                        return False, msg

                    self.specAnPowerHistory.pHotLSB = self.spectrumAnalyzer.traceY
                    for freqIF, amp in zip(self.ifSteps, self.spectrumAnalyzer.traceY):
                        record = self.rawDataRecords[(freqLO, freqIF, pol)]
                        record.Phot_LSB = amp

                    self.chopper.gotoCold()
                    
                    self.externalSwitch.setPolAndSideband(pol, 'USB')
                    success, msg = self.spectrumAnalyzer.readTrace()
                    if not success:
                        return False, msg

                    self.specAnPowerHistory.pColdUSB = self.spectrumAnalyzer.traceY
                    for freqIF, amp in zip(self.ifSteps, self.spectrumAnalyzer.traceY):
                        record = self.rawDataRecords[(freqLO, freqIF, pol)]
                        record.Pcold_USB = amp

                    self.externalSwitch.setPolAndSideband(pol, 'LSB')
                    success, msg = self.spectrumAnalyzer.readTrace()
                    if not success:
                        return False, msg

                    self.specAnPowerHistory.pColdLSB = self.spectrumAnalyzer.traceY
                    for freqIF, amp in zip(self.ifSteps, self.spectrumAnalyzer.traceY):
                        record = self.rawDataRecords[(freqLO, freqIF, pol)]
                        record.Pcold_LSB = amp

        return True, ""

    def __measureNoiseTempSpin(self, freqLO: float, freqIF: float, pol: int, sideband: str) -> tuple[bool, str]:
        self.warmIFPlate.inputSwitch.setPolAndSideband(pol, sideband)
        time.sleep(0.5)
        sampleInterval = 1 / self.commonSettings.sampleRate
        self.chopperPowerHistory = []
        samplesHot = []
        samplesCold = []
        done = False
        chopperPower = ChopperPowers(input = f"Pol{pol} {sideband}")
        self.currentRecords[pol] = record = self.rawDataRecords[(freqLO, freqIF, pol)]

        while not done:
            cycleEnd = time.time() + sampleInterval
            
            chopperPower.chopperState = self.chopper.getState()
            chopperPower.power = self.powerMeter.read()
            
            self.chopperPowerHistory.append(copy.copy(chopperPower))                    
            
            if chopperPower.chopperState == State.OPEN:
                samplesHot.append(chopperPower.power)
            elif chopperPower.chopperState == State.CLOSED:
                samplesCold.append(chopperPower.power)
            
            if len(samplesHot) >= self.commonSettings.powerMeterConfig.maxS and len(samplesCold) >= self.commonSettings.powerMeterConfig.maxS:                        
                done = True
            elif len(samplesHot) >= self.commonSettings.powerMeterConfig.minS and len(samplesCold) >= self.commonSettings.powerMeterConfig.minS:
                pHotErr = stdev(samplesHot) / sqrt(len(samplesHot))
                pColdErr = stdev(samplesCold) / sqrt(len(samplesCold))
                if pHotErr <= self.commonSettings.powerMeterConfig.stdErr and pColdErr <= self.commonSettings.powerMeterConfig.stdErr:
                    done = True
        
            now = time.time()
            if now < cycleEnd:
                time.sleep(cycleEnd - now)

        if sideband == 'USB':
            record.Phot_USB = 10 * log10(mean(samplesHot) * 1000)
            record.Pcold_USB = 10 * log10(mean(samplesCold) * 1000)
            record.Phot_USB_StdErr = pHotErr
            record.Pcold_USB_StdErr = pColdErr
        else:
            record.Phot_LSB = 10 * log10(mean(samplesHot) * 1000)
            record.Pcold_LSB = 10 * log10(mean(samplesCold) * 1000)
            record.Phot_LSB_StdErr = pHotErr
            record.Pcold_LSB_StdErr = pColdErr
        return True, ""

    def __rfSourceAutoLevel(self, freqIF: float) -> tuple[bool, str]:
        if SIMULATE:
            return (True, "")

        setValue = 15 # percent
        maxIter = 25
        setPoint = self.commonSettings.imageRejectSBTarget_PM
        if self.commonSettings.backEndMode == BackEndMode.SPEC_AN.value:
            setPoint = self.commonSettings.imageRejectSBTarget_SA

        controller = BinarySearchController(
            outputRange = [15, 100], 
            initialStepPercent = 5, 
            initialOutput = setValue, 
            setPoint =  setPoint, 
            tolerance = 3,
            maxIter = maxIter)
        
        self.rfSrcDevice.setPAOutput(self.rfSrcDevice.paPol, setValue)
        if self.commonSettings.backEndMode == BackEndMode.SPEC_AN.value:
            self.spectrumAnalyzer.configNarrowBand(freqIF, 0.0001)
            self.spectrumAnalyzer.measureNarrowBand()
            amp = self.spectrumAnalyzer.markerY
        else:            
            amp = self.powerMeter.read()
        
        done = error = False
        msg = ""
        iter = 0

        if not amp:
            error = True
        while not done and not error: 
            iter += 1
            if iter >= maxIter or setValue >= 100:
                error = True
                msg = f"__rfSourceAutoLevel: iter={iter} maxIter={maxIter} setValue={setValue}%"
            elif (controller.isComplete()):
                done = True
                msg = f"__rfSourceAutoLevel: success iter={iter} setValue={setValue}% amp={amp:.1f} dBm"
            else:
                controller.process(amp)
                setValue = controller.output
                self.rfSrcDevice.setPAOutput(self.rfSrcDevice.paPol, setValue)
                time.sleep(0.2)
                if self.commonSettings.backEndMode == BackEndMode.SPEC_AN.value:
                    self.spectrumAnalyzer.measureNarrowBand()
                    amp = self.spectrumAnalyzer.markerY
                else:            
                    amp = self.powerMeter.read()
                if amp is None:
                    error = True
                    msg = f"__rfSourceAutoLevel: powerMeter.read error at iter={iter}."
                self.logger.info(f"__rfSourceAutoLevel: iter={iter} setValue={setValue}% amp={amp:.1f} dBm")

        if error:
            self.logger.error(msg)
        elif msg:
            self.logger.info(msg)
        return (not error, msg)

    def __attenuatorAutoLevel(self):
        self.measurementStatus.setStatusMessage("Setting attenuator...")
        self.chopper.stop()
        self.chopper.gotoHot()
        self.powerMeter.setUnits(Unit.DBM)
        self.warmIFPlate.inputSwitch.setValue(InputSelect.POL0_USB)
        time.sleep(1.0)

        # treating (max - atten) as gain because BinarySearchController wants the input to go up when the output does.
        setValue = 100 - self.ifAtten
        maxIter = 25
        
        controller = BinarySearchController(
            outputRange = [0, 100], 
            initialStepPercent = 5, 
            initialOutput = setValue, 
            setPoint = self.commonSettings.targetPHot,
            tolerance = 0.5,
            maxIter = maxIter)

        self.warmIFPlate.attenuator.setValue(100 - setValue)
        time.sleep(0.25)
        amp = self.powerMeter.read(averaging = 10)

        done = error = False
        msg = ""
        iter = 0

        if not amp:
            error = True
        while not done and not error: 
            iter += 1
            if iter >= maxIter:
                error = True
                msg = f"__attenuatorAutoLevel: iter={iter} maxIter={maxIter} setValue={100 - setValue} dB"
            elif controller.isComplete():
                done = True
                msg = f"__attenuatorAutoLevel: success iter={iter} amp={amp:.1f} dBm setValue={100 - setValue} dB"
            else:
                controller.process(amp)
                setValue = int(round(controller.output))
                self.warmIFPlate.attenuator.setValue(100 - setValue)
                time.sleep(0.25)
                amp = self.powerMeter.read(averaging = 10)
                if amp is None:
                    error = True
                    msg = f"__attenuatorAutoLevel: powerMeter.read error at iter={iter}."
                self.logger.info(f"__attenuatorAutoLevel: iter={iter} amp={amp:.1f} dBm setValue={100 - setValue} dB")

        if error:
            self.logger.error(msg)
        elif msg:
            self.logger.info(msg)
        self.ifAtten = 100 - setValue
        return (not error, msg)

    def __rfSourceOff(self) -> tuple[bool, str]:
        self.rfSrcDevice.setPAOutput(pol = self.rfSrcDevice.paPol, percent = 0)
        return (True, "")

    def checkColdLoad(self) -> tuple[bool, str]:
        shouldPause, msg = self.coldLoadController.shouldPause(enablePause = self.commonSettings.pauseForColdLoad)
        while shouldPause and not self.stopNow:
            self.measurementStatus.setStatusMessage("Cold load " + msg)
            time.sleep(10)
            shouldPause, msg = self.coldLoadController.shouldPause(enablePause = self.commonSettings.pauseForColdLoad)
        
        if self.stopNow:
            self.finished = True                
            return True, "User stop"

        return True, msg
    
