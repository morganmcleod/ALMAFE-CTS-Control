import sys
import logging
from typing import Optional
from socket import getfqdn
import concurrent.futures
from app_Common.CTSDB import CTSDB
import app_Common.MeasurementStatus
measurementStatus = app_Common.MeasurementStatus.measurementStatus()
import app_CTS.measProcedure.BeamScanner
beamScanner = app_CTS.measProcedure.BeamScanner.beamScanner
from DBBand6Cart.CartTests import CartTest
from app_Common.CTSDB import CartTestsDB
from DBBand6Cart.TestTypes import TestTypeIds
from DebugOptions import *

class ScriptRunner():
    BIAS_OPT_MODULE = "app.scripts.BiasOptimization"
    IV_CURVES_MODULE = "app.scripts.IVCurves"
    MAGNET_OPT_MODULE = "app.scripts.MagnetOptimization"
    DEFLUX_MODULE = "app.scripts.MixerDeflux"
    NOISE_TEMP_MODULE = "app.scripts.NoiseTemperature"
    Y_FACTOR_MODULE = "app.scripts.YFactor"
    AMP_STABILITY_MODULE = "app.scripts.AmplitudeStability"
    PHASE_STABILITY_MODULE = "app.scripts.PhaseStability"
    ENTRY_FUNCTION = "main"

    def __init__(self) -> None:
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers = 1)
        self.future = None

    def get_status(self):
        return measurementStatus.getCurrentValues()
    
    def get_carttest(self) -> Optional[CartTest]:
        return measurementStatus.getMeasuring()

    def start(self, cartTest:CartTest, **kwargs) -> tuple[bool, str]:
        if measurementStatus.isMeasuring():
            msg = "A measurement is already in progress."
            self.logger.error(msg)
            return False, msg

        try:
            testType = TestTypeIds(cartTest.fkTestType)
        except:
            msg = f"Test type {cartTest.fkTestType} is not supported"
            self.logger.error(msg)
            return False, msg

        cartTestsDb = CartTestsDB()

        cartTest.testSysName = getfqdn()
        if testType == TestTypeIds.BEAM_PATTERN:
            cartTest.key = beamScanner.start(cartTest)
            measurementStatus.setMeasuring(cartTest)
            return True, "Beam scans started."

        elif testType in (TestTypeIds.NOISE_TEMP, TestTypeIds.LO_WG_INTEGRITY, TestTypeIds.IF_PLATE_NOISE):
            testSteps = kwargs.get('testSteps', None)

            if testSteps:
                # if we are measuring noise temperature then make that the master CartTests record
                if testSteps.noiseTemp or self.testSteps.imageReject:
                    testType = TestTypeIds.NOISE_TEMP
                # if not noise temp but LO WG integrity, make that the master record:
                elif testSteps.loWGIntegrity:
                    testType = TestTypeIds.LO_WG_INTEGRITY
                # if only measuring warm IF noise:
                elif testSteps.warmIF:
                    testType = TestTypeIds.IF_PLATE_NOISE

            if SIMULATE:
                cartTest.key = 1
            else:
                cartTest.key = cartTestsDb.create(cartTest)
            measurementStatus.setMeasuring(cartTest)
            success, msg = self._run_script(self.NOISE_TEMP_MODULE)
            if success:
                return True, f"{testType.name} started."
            else:
                return False, msg

        elif testType == TestTypeIds.OPTIMUM_BIAS:
            testType = TestTypeIds.NOISE_TEMP

            if SIMULATE:
                cartTest.key = 1
            else:
                cartTest.key = cartTestsDb.create(cartTest)

            measurementStatus.setMeasuring(cartTest)
            success, msg = self._run_script(self.BIAS_OPT_MODULE)
            if success:
                return True, f"{testType.name} started."
            else:
                return False, msg
        
        elif testType == TestTypeIds.Y_FACTOR:
            cartTest.key = 0
            cartTest.description = "Y-factor"
            measurementStatus.setMeasuring(cartTest)
            success, msg = self._run_script(self.Y_FACTOR_MODULE)
            if success:
                return True, f"{testType.name} started."
            else:
                return False, msg

        elif testType == TestTypeIds.AMP_STABILITY:
            if SIMULATE:
                cartTest.key = 1
            else:
                cartTest.key = cartTestsDb.create(cartTest)
            measurementStatus.setMeasuring(cartTest)
            success, msg = self._run_script(self.AMP_STABILITY_MODULE)
            if success:
                return True, f"{testType.name} started."
            else:
                return False, msg
        
        elif testType == TestTypeIds.PHASE_STABILITY:
            if SIMULATE:
                cartTest.key = 1
            else:
                cartTest.key = cartTestsDb.create(cartTest)
            measurementStatus.setMeasuring(cartTest)
            success, msg = self._run_script(self.PHASE_STABILITY_MODULE)
            if success:
                return True, f"{testType.name} started."
            else:
                return False, msg
        
        elif testType == TestTypeIds.IV_CURVES:
            cartTest.key = 0
            cartTest.description = "I-V Curves"
            measurementStatus.setMeasuring(cartTest)
            success, msg = self._run_script(self.IV_CURVES_MODULE)
            if success:
                return True, f"{testType.name} started."
            else:
                return False, msg

        elif testType == TestTypeIds.MAGNET_OPTIMIZATION:
            cartTest.key = 0
            cartTest.description = "Magnet Optimization"
            measurementStatus.setMeasuring(cartTest)
            success, msg = self._run_script(self.MAGNET_OPT_MODULE)
            if success:
                return True, f"{testType.name} started."
            else:
                return False, msg

        elif testType == TestTypeIds.MIXER_DEFLUX:
            cartTest.key = 0
            cartTest.description = "Mixer Deflux"
            measurementStatus.setMeasuring(cartTest)
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
        cartTest = measurementStatus.getMeasuring()        
        if not cartTest:
            msg = "No measurement is in progress."
            self.logger.warn(msg)
            return False, msg
        
        testType = TestTypeIds(cartTest.fkTestType)

        if testType in (
                TestTypeIds.NOISE_TEMP, 
                TestTypeIds.LO_WG_INTEGRITY, 
                TestTypeIds.IF_PLATE_NOISE, 
                TestTypeIds.Y_FACTOR, 
                TestTypeIds.OPTIMUM_BIAS,
                TestTypeIds.IV_CURVES,
                TestTypeIds.MAGNET_OPTIMIZATION,
                TestTypeIds.MIXER_DEFLUX,
                TestTypeIds.IV_CURVES
            ):
            measurementStatus.stopMeasuring()
            return True, f"{TestTypeIds(testType).name} stopped."
        elif testType == TestTypeIds.BEAM_PATTERN:
            beamScanner.stop()
            measurementStatus.stopMeasuring()
            return True, "Beam scans stopped."
        elif testType == TestTypeIds.AMP_STABILITY:
            measurementStatus.stopMeasuring()
            return True, "Amplitude stability stopped."
        elif testType == TestTypeIds.PHASE_STABILITY:
            measurementStatus.stopMeasuring()
            return True, "Phase stability stopped."
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
        except:
            return False, f"Coudld not import {module_name}"
        
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
        fun = getattr(module, function)
        try:
            self.future = self.executor.submit(fun)
        except:
            return False, f"Could not run function '{function}' in {module_name}"

        # register the callback to run after the script exits for any reason:
        self.future.add_done_callback(done_callback)
        return True, ""
