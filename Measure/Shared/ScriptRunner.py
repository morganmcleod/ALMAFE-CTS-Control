import logging
from typing import Optional
from socket import getfqdn
import concurrent.futures
from app.scripts.BiasOptimization import bias_optimization
from app.scripts.NoiseTemperature import noise_temperature
from app.scripts.YFactor import y_factor
from app.database.CTSDB import CTSDB
from app.measProcedure.MeasurementStatus import measurementStatus
from app.measProcedure.BeamScanner import beamScanner
from app.measProcedure.Stability import amplitudeStablilty, phaseStability
from DBBand6Cart.CartTests import CartTest, CartTests
from DBBand6Cart.TestTypes import TestTypeIds
from DebugOptions import *

class ScriptRunner():
    def __init__(self) -> None:
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers = 1)

    def get_status(self):
        return measurementStatus.getCurrentValues()
    
    def get_carttest(self) -> Optional[CartTest]:
        return measurementStatus.getMeasuring()

    def start(self, cartTest:CartTest, **kwargs) -> tuple[bool, str]:
        if measurementStatus.isMeasuring():
            msg = "A measurement is already in progress."
            self.logger.error(msg)
            return False, msg

        cartTestsDb = CartTests(driver = CTSDB())        

        cartTest.testSysName = getfqdn()
        if cartTest.fkTestType == TestTypeIds.BEAM_PATTERN.value:
            cartTest.key = beamScanner.start(cartTest)
            measurementStatus.setMeasuring(cartTest)
            return True, "Beam scans started."

        elif cartTest.fkTestType in (TestTypeIds.NOISE_TEMP.value, TestTypeIds.LO_WG_INTEGRITY, TestTypeIds.IF_PLATE_NOISE):
            testSteps = kwargs.get('testSteps', None)

            if testSteps:
                # if we are measuring noise temperature then make that the master CartTests record
                if testSteps.noiseTemp or self.testSteps.imageReject:
                    cartTest.fkTestType = TestTypeIds.NOISE_TEMP.value
                # if not noise temp but LO WG integrity, make that the master record:
                elif testSteps.loWGIntegrity:
                    cartTest.fkTestType = TestTypeIds.LO_WG_INTEGRITY.value
                # if only measuring warm IF noise:
                elif testSteps.warmIF:
                    cartTest.fkTestType = TestTypeIds.IF_PLATE_NOISE.value

            if SIMULATE:
                cartTest.key = 1
            else:
                cartTest.key = cartTestsDb.create(cartTest)
            measurementStatus.setMeasuring(cartTest)
            self.futures = []
            self.futures.append(self.executor.submit(noise_temperature))            
            return True, f"{TestTypeIds(cartTest.fkTestType).name} started."

        elif cartTest.fkTestType == TestTypeIds.OPTIMUM_BIAS.value:
            cartTest.fkTestType = TestTypeIds.NOISE_TEMP.value

            if SIMULATE:
                cartTest.key = 1
            else:
                cartTest.key = cartTestsDb.create(cartTest)

            measurementStatus.setMeasuring(cartTest)
            self.futures = []
            self.futures.append(self.executor.submit(bias_optimization))            
            return True, f"{TestTypeIds(cartTest.fkTestType).name} started."
        
        elif cartTest.fkTestType == TestTypeIds.Y_FACTOR.value:
            cartTest.key = 0
            cartTest.description = "Y-factor"
            measurementStatus.setMeasuring(cartTest)
            self.futures = []
            self.futures.append(self.executor.submit(y_factor))            
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
        cartTest = measurementStatus.getMeasuring()        
        if not cartTest:
            msg = "No measurement is in progress."
            self.logger.warn(msg)
            return False, msg
        
        testType = TestTypeIds(cartTest.fkTestType)

        if testType == TestTypeIds.BEAM_PATTERN:
            beamScanner.stop()
            measurementStatus.stopMeasuring()
            return True, "Beam scans stopped."
        elif testType in (TestTypeIds.NOISE_TEMP, TestTypeIds.LO_WG_INTEGRITY, TestTypeIds.IF_PLATE_NOISE, TestTypeIds.Y_FACTOR, TestTypeIds.OPTIMUM_BIAS):
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