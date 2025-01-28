import sys
import logging
from typing import Optional
from socket import getfqdn
import concurrent.futures
from app_Common.CTSDB import MixerTestsDB
import app_Common.measProcedure.MeasurementStatus
measurementStatus = app_Common.measProcedure.MeasurementStatus.measurementStatus()
import app_MTS2.measProcedure.NoiseTemperature
testSteps = app_MTS2.measProcedure.NoiseTemperature.settingsContainer.testSteps
from DBBand6Cart.MixerTests import MixerTest, MixerTests
from DBBand6Cart.TestTypes import TestTypeIds
from Measure.NoiseTemperature.schemas import TestSteps
from DebugOptions import *

class ScriptRunner():
    BIAS_OPT_MODULE = "app_MTS2.scripts.BiasOptimization"
    IV_CURVES_MODULE = "app_MTS2.scripts.IVCurves"
    MAGNET_OPT_MODULE = "app_MTS2.scripts.MagnetOptimization"
    DEFLUX_MODULE = "app_MTS2.scripts.MixerDeflux"
    NOISE_TEMP_MODULE = "app_MTS2.scripts.NoiseTemperature"
    Y_FACTOR_MODULE = "app_MTS2.scripts.YFactor"
    ENTRY_FUNCTION = "main"

    def __init__(self) -> None:
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers = 1)
        self.testSysName = getfqdn()
        self.future = None

    def get_status(self):
        return measurementStatus.getCurrentValues()
    
    def get_mixertest(self) -> Optional[MixerTest]:
        return measurementStatus.getMeasuring()

    def start(self, testRecord: MixerTest, **kwargs) -> tuple[bool, str]:
        if measurementStatus.isMeasuring():
            msg = "A measurement is already in progress."
            self.logger.error(msg)
            return False, msg

        try:
            testType = TestTypeIds(testRecord.fkTestType)
        except:
            msg = f"Test type {testRecord.fkTestType} is not supported"
            self.logger.error(msg)
            return False, msg

        mixerTestsDb = MixerTestsDB()
        testRecord.testSysName = self.testSysName

        if testType in (TestTypeIds.NOISE_TEMP, TestTypeIds.IF_PLATE_NOISE):
            # if we are measuring noise temperature then make that the master CartTests record
            if testSteps.noiseTemp or testSteps.imageReject:
                testType = TestTypeIds.NOISE_TEMP
            # if only measuring warm IF noise:
            elif testSteps.warmIF:
                testType = TestTypeIds.IF_PLATE_NOISE

            if SIMULATE:
                testRecord.key = 1
            else:
                testRecord.key = mixerTestsDb.create(testRecord)
            measurementStatus.setMeasuring(testRecord)
            success, msg = self._run_script(self.NOISE_TEMP_MODULE)
            if success:
                return True, f"{testType.name} started."
            else:
                return False, msg

        elif testType == TestTypeIds.OPTIMUM_BIAS:
            # we actually want to write a noise temperature test record:
            testRecord.fkTestType = TestTypeIds.NOISE_TEMP.value
            if SIMULATE:
                testRecord.key = 1
            else:
                testRecord.key = mixerTestsDb.create(testRecord)

            measurementStatus.setMeasuring(testRecord)
            success, msg = self._run_script(self.BIAS_OPT_MODULE)
            if success:
                return True, f"{testType.name} started."
            else:
                return False, msg
        
        elif testType == TestTypeIds.Y_FACTOR:
            testRecord.key = 0
            testRecord.description = "Y-factor"
            measurementStatus.setMeasuring(testRecord)
            success, msg = self._run_script(self.Y_FACTOR_MODULE)
            if success:
                return True, f"{testType.name} started."
            else:
                return False, msg

        elif testType == TestTypeIds.IV_CURVES:
            if SIMULATE:
                testRecord.key = 1
            else:
                testRecord.key = mixerTestsDb.create(testRecord)
            measurementStatus.setMeasuring(testRecord)
            success, msg = self._run_script(self.IV_CURVES_MODULE)
            if success:
                return True, f"{testType.name} started."
            else:
                return False, msg

        elif testType == TestTypeIds.MAGNET_OPTIMIZATION:
            testRecord.key = 0
            testRecord.description = "Magnet Optimization"
            measurementStatus.setMeasuring(testRecord)
            success, msg = self._run_script(self.MAGNET_OPT_MODULE)
            if success:
                return True, f"{testType.name} started."
            else:
                return False, msg

        elif testType == TestTypeIds.MIXER_DEFLUX:
            testRecord.key = 0
            testRecord.description = "Mixer Deflux"
            measurementStatus.setMeasuring(testRecord)
            success, msg = self._run_script(self.DEFLUX_MODULE)
            if success:
                return True, f"{testType.name} started."
            else:
                return False, msg

        else:
            msg = f"Nothing to do for test type {testType}."
            self.logger.error(msg)
            return False

    def stop(self) -> tuple[bool, str]:
        testRecord = measurementStatus.getMeasuring()        
        if not testRecord:
            msg = "No measurement is in progress."
            self.logger.warn(msg)
            return False, msg
        
        testType = TestTypeIds(testRecord.fkTestType)

        if testType in (
                TestTypeIds.NOISE_TEMP, 
                TestTypeIds.IF_PLATE_NOISE, 
                TestTypeIds.Y_FACTOR, 
                TestTypeIds.OPTIMUM_BIAS,
                TestTypeIds.IV_CURVES,
                TestTypeIds.MAGNET_OPTIMIZATION,
                TestTypeIds.MIXER_DEFLUX,
                TestTypeIds.IV_CURVES
            ):
            measurementStatus.stopMeasuring()
            return True, f"{testType.name} stopped."
        else:
            msg = f"Nothing to do for test type {testType}."
            self.logger.error(msg)
            return False, msg
        
    def _run_script(self, module_name:str, function:str = 'main') -> tuple[bool, str]:
        # wait for any exising script to finish:
        if self.future is not None:
            try:
                self.future.result()
            except:
                pass
        self.future = None
        # unload the script module:
        try:
            if module_name in sys.modules:
                del sys.modules[module_name]
        except:
            pass

        # import the script module:
        try:
            __import__(module_name)            
        except Exception as e:
            msg = f"Exception loading script: {str(e)}"
            self.logger.error(msg)
            measurementStatus.setError(msg)
            return False, msg
        
        # define callback for when script finishes or there's an exeption:
        def done_callback(future: concurrent.futures.Future):
            try:
                future.result()
            except Exception as e:
                msg = f"Exception in {module_name}: {str(e)}"
                self.logger.error(msg)
                measurementStatus.setError(msg)

        # run the script funciton:
        module = sys.modules[module_name]
        try:
            fun = getattr(module, function)
            self.future = self.executor.submit(fun)
        except Exception as e:
            msg = f"Exception runnning script: {str(e)}"
            self.logger.error(msg)
            measurementStatus.setError(msg)
            return False, msg

        # register the callback to run after the script exits for any reason:
        self.future.add_done_callback(done_callback)
        return True, ""
