import logging
from socket import getfqdn
from typing import Optional, Union
import copy

from DBBand6Cart.CartTests import CartTest
from DBBand6Cart.TestTypes import TestTypeIds

from hardware.FEMC import ccaDevice, loDevice, rfSrcDevice, cartAssembly, femcDevice
from hardware.ReferenceSources import loReference, rfReference
from hardware.WarmIFPlate import warmIFPlate
from hardware.BeamScanner import motorController, pna
from hardware.NoiseTemperature import chopper, coldLoad, powerMeter, powerSupply, temperatureMonitor
from hardware.Stability import voltMeter

from measProcedure.BeamScanner import beamScanner
from measProcedure.NoiseTemperature import noiseTemperature, yFactor
from measProcedure.Stability import amplitudeStablilty, phaseStability
from measProcedure.MeasurementStatus import measurementStatus

from Measure.Shared.MeasurementStatus import MeasurementStatus
from Measure.NoiseTemperature.schemas import CommonSettings, WarmIFSettings, NoiseTempSettings

def override(parent_class):
    def overrider(method):
        assert(method.__name__ in dir(parent_class))
        return method
    return overrider

class CTSMeasure():
    def __init__(self) -> None:
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
    
    def get_status(self) -> MeasurementStatus:
        return measurementStatus.getCurrentValues()
        
    def get_carttest(self) -> Optional[CartTest]:
        testType = self.__get_testtype()
        if not testType:
            return None
        elif testType == TestTypeIds.BEAM_PATTERN:
            if beamScanner.isMeasuring():
                return measurementStatus.getMeasuring()
        elif testType in (TestTypeIds.NOISE_TEMP, TestTypeIds.LO_WG_INTEGRITY, TestTypeIds.IF_PLATE_NOISE):
            if noiseTemperature.isMeasuring():
                return measurementStatus.getMeasuring()
        elif testType == TestTypeIds.AMP_STABILITY:
            if amplitudeStablilty.isMeasuring():
                return measurementStatus.getMeasuring()
        elif testType == TestTypeIds.PHASE_STABILITY:
            if phaseStability.isMeasuring():
                return measurementStatus.getMeasuring()
        return None

    def start(self, cartTest:CartTest) -> tuple[bool, str]:
        if measurementStatus.isMeasuring():
            msg = "A measurement is already in progress."
            self.logger.error(msg)
            return False, msg
        
        cartTest.testSysName = getfqdn()
        if cartTest.fkTestType == TestTypeIds.BEAM_PATTERN.value:
            cartTest.key = beamScanner.start(cartTest)
            measurementStatus.setMeasuring(cartTest)
            return True, "Beam scans started."
        elif cartTest.fkTestType in (TestTypeIds.NOISE_TEMP.value, TestTypeIds.LO_WG_INTEGRITY, TestTypeIds.IF_PLATE_NOISE):
            cartTest.key = noiseTemperature.start(cartTest)
            measurementStatus.setMeasuring(cartTest)
            return True, f"{TestTypeIds(cartTest.fkTestType).name} started."
        elif cartTest.fkTestType == TestTypeIds.AMP_STABILITY.value:
            cartTest.key = amplitudeStablilty.start(cartTest)
            measurementStatus.setMeasuring(cartTest)
            return True, "Amplitude stability started"
        elif cartTest.fkTestType == TestTypeIds.PHASE_STABILITY.value:
            cartTest.key = phaseStability.start(cartTest)
            measurementStatus.setMeasuring(cartTest)
            return True, "Phase stability started"
        else:
            msg = f"Nothing to do for test type {cartTest.fkTestType}."
            self.logger.error(msg)
            return False

    def stop(self) -> tuple[bool, str]:
        testType = self.__get_testtype()
        if not testType:
            msg = "No measurement is in progress."
            self.logger.warn(msg)
            return False, msg
        
        if testType == TestTypeIds.BEAM_PATTERN:
            beamScanner.stop()
            measurementStatus.stopMeasuring()
            return True, "Beam scans stopped."
        elif testType in (TestTypeIds.NOISE_TEMP, TestTypeIds.LO_WG_INTEGRITY, TestTypeIds.IF_PLATE_NOISE):
            noiseTemperature.stop()
            measurementStatus.stopMeasuring()
            return True, f"{TestTypeIds(testType).name} stopped."
        elif testType == TestTypeIds.AMP_STABILITY:
            amplitudeStablilty.stop()
            measurementStatus.stopMeasuring()
            return True, "Amplitude stability stopped."
        elif testType == TestTypeIds.PHASE_STABILITY:
            phaseStability.stop()
            measurementStatus.stopMeasuring()
            return True, "Phase stability stopped."
        else:
            msg = f"Nothing to do for test type {testType}."
            self.logger.error(msg)
            return False, msg
        
    def __get_testtype(self) -> Optional[TestTypeIds]:
        cartTest = measurementStatus.getMeasuring()
        try:
            return TestTypeIds(cartTest.fkTestType)    
        except:
            return None        

class CTSNoiseTemp(CTSMeasure):
    def __init__(self) -> None:
        super().__init__()

    @override
    def start(self, cartTest:CartTest, ifMode: str = 'step', chopperMode:str = 'spin') -> tuple[bool, str]:
        if measurementStatus.isMeasuring():
            msg = "A measurement is already in progress."
            self.logger.error(msg)
            return False, msg
        measurementStatus.setMeasuring(cartTest)
        noiseTemperature.noiseTemp.ifMode = ifMode
        noiseTemperature.noiseTemp.chopperMode = chopperMode
        return True, f"begin_scripted_test: {cartTest.getText()}"
    
    @override
    def stop(self) -> tuple[bool, str]:
        testType = self.__get_testtype()
        if not testType:
            msg = "No measurement is in progress."
            self.logger.warn(msg)
            return False, msg
        if testType not in (TestTypeIds.NOISE_TEMP.value, TestTypeIds.LO_WG_INTEGRITY.value, TestTypeIds.IF_PLATE_NOISE.value):
            msg = "Running measurement is not noise temperature."
            self.logger.error(msg)
            return False, msg
        noiseTemperature.finish()
        measurementStatus.stopMeasuring()
        return True, f"{TestTypeIds(testType).name} stopped."

    def get_common_settings(self) -> CommonSettings:
        return copy.copy(noiseTemperature.commonSettings)
    
    def set_common_settings(self, commonSettings: CommonSettings) -> None:
        noiseTemperature.updateSettings(commonSettings = commonSettings)

    def get_nt_settings(self) -> NoiseTempSettings:
        return copy.copy(noiseTemperature.noiseTempSettings)
    
    def set_nt_settings(self, noiseTempSettings: NoiseTempSettings) -> None:
        noiseTemperature.updateSettings(noiseTempSettings = noiseTempSettings)

    def get_lo_wg_settings(self) -> NoiseTempSettings:
        return copy.copy(noiseTemperature.loWgIntegritySettings)
    
    def set_lo_wg_settings(self, noiseTempSettings: NoiseTempSettings) -> None:
        noiseTemperature.updateSettings(loWgIntegritySettings = noiseTempSettings)

    def get_warm_if_settings(self) -> WarmIFSettings:
        return copy.copy(noiseTemperature.warmIFSettings)
    
    def set_warm_if_settings(self, warmIFSettings: WarmIFSettings) -> None:
        noiseTemperature.updateSettings(warmIFSettings = warmIFSettings)

    def set_lo(self, freqLO: float = 0, step: str = None, setBias: bool = True) -> tuple[bool, str]:
        """Go to a specific LO frequency or to the next frequency in the measurement list

        :param float freqLO GHz, defaults to 0
        :param str step defaults to None: supported values are 'first' or 'next'
        :param bool setBias defaults to True: if true, set the SIS bias and LO power
        :return tuple[bool, str]: success, msg
        """
        success, msg = self.__checkTestType()
        if not success:
            return success, msg

        if step in ('first', 'next'):
            return noiseTemperature.noiseTemp.setLO(step = step, setBias = setBias)
        else:
            return noiseTemperature.noiseTemp.setLO(freqLO, setBias = setBias)
    
    def set_modes(self, if_mode: str = 'step', chopper_mode: str = 'spin') -> tuple[bool, str]:
        success, msg = self.__checkTestType()
        if not success:
            return success, msg
        if if_mode.lower() in ('step', 'sweep', 'sa_sweep'):
            noiseTemperature.noiseTemp.ifMode = if_mode.lower()
        else:
            return False, f"Unsupported if_mode: {if_mode}"
        if chopper_mode.lower() in ('spin', 'switch'):
            noiseTemperature.noiseTemp.chopperMode = chopper_mode.lower()
        else:
            return False, f"Unsupported if_mode: {if_mode}"
        return True, ""

    def set_if(self, freqIF: float = 0, step: str = None, attenuatorAutoLevel: bool = True) -> tuple[bool, str]:
        success, msg = self.__checkTestType()
        if not success:
            return success, msg
        if noiseTemperature.noiseTemp.ifMode != 'step':
            return False, f"Can't set IF when in if_mode '{noiseTemperature.noiseTemp.ifMode}'"
        if step in ('first', 'next'):
            return noiseTemperature.noiseTemp.setIF(step = step, attenuatorAutoLevel = attenuatorAutoLevel)
        else:
            return noiseTemperature.noiseTemp.setIF(freqIF, attenuatorAutoLevel = attenuatorAutoLevel)

    def check_cold_load(self):
        success, msg = self.__checkTestType()
        if not success:
            return success, msg
        return noiseTemperature.checkColdLoad()
    
    # def measure_warm_if(self)
   
    def measure_ir(self) -> tuple[bool, str]:
        success, msg = self.__checkTestType()
        if not success:
            return success, msg
        return noiseTemperature.noiseTemp.measureImageReject()
    
    def measure_nt(self) -> tuple[bool, str]:
        success, msg = self.__checkTestType()
        if not success:
            return success, msg
        return noiseTemperature.noiseTemp.measureNoiseTemp()

    def __checkTestType(self) -> tuple[bool, str]:
        testType = self.__get_testtype()
        if not testType:
            msg = "No measurement is in progress."
            self.logger.warn(msg)
            return False, msg
        if testType not in (TestTypeIds.NOISE_TEMP.value, TestTypeIds.LO_WG_INTEGRITY.value, TestTypeIds.IF_PLATE_NOISE.value):
            msg = "Running measurement is not noise temperature."
            self.logger.error(msg)
            return False, msg

