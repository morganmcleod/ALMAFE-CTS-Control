from fastapi import APIRouter
from Response import KeyResponse, MessageResponse
from typing import Optional
from socket import getfqdn
from DBBand6Cart.CartTests import CartTest
from DBBand6Cart.TestTypes import TestTypeIds
from Measure.Shared.MeasurementStatus import MeasurementStatus

# Import global objects from measProcedure:
from app.measProcedure.BeamScanner import beamScanner
from app.measProcedure.NoiseTemperature import noiseTemperature
from app.measProcedure.Stability import amplitudeStablilty, phaseStability
from app.measProcedure.MeasurementStatus import measurementStatus

from DebugOptions import *

import logging
logger = logging.getLogger("ALMAFE-CTS-Control")

router = APIRouter(prefix="/measure")

@router.put("/start", response_model = KeyResponse)
async def put_Start(cartTest:CartTest):
    if measurementStatus.isMeasuring():
        return KeyResponse(key = 0, message = "A measurement is already in progress.", success = False)    
    cartTest.testSysName = getfqdn()
    if cartTest.fkTestType == TestTypeIds.BEAM_PATTERN.value:
        cartTestId = beamScanner.start(cartTest)
        measurementStatus.setMeasuring(cartTest)
        return KeyResponse(key = cartTestId, message = "Beam scans started", success = True)
    elif cartTest.fkTestType in (TestTypeIds.NOISE_TEMP.value, TestTypeIds.LO_WG_INTEGRITY, TestTypeIds.IF_PLATE_NOISE):
        cartTestId = noiseTemperature.start(cartTest)
        measurementStatus.setMeasuring(cartTest)
        return KeyResponse(key = cartTestId, message = f"{TestTypeIds(cartTest.fkTestType).name} started", success = True)
    elif cartTest.fkTestType == TestTypeIds.AMP_STABILITY.value:
        cartTestId = amplitudeStablilty.start(cartTest)
        measurementStatus.setMeasuring(cartTest)
        return KeyResponse(key = cartTestId, message = "Amplitude stability started", success = True)
    elif cartTest.fkTestType == TestTypeIds.PHASE_STABILITY.value:
        cartTestId = phaseStability.start(cartTest)
        measurementStatus.setMeasuring(cartTest)
        return KeyResponse(key = cartTestId, message = "Phase stability started", success = True)
    else:
        return KeyResponse(key = 0, message = f"Nothing to do for test type {cartTest.fkTestType}", success = False)

@router.put("/stop", response_model = MessageResponse)
async def put_Stop():
    cartTest = measurementStatus.getMeasuring()
    if not cartTest:
        return MessageResponse(message = "Nothing to do", success = False)
    if cartTest.fkTestType == TestTypeIds.BEAM_PATTERN.value:
        beamScanner.stop()
        measurementStatus.stopMeasuring()
        return MessageResponse(message = "Beam scans stopped", success = True)
    elif cartTest.fkTestType in (TestTypeIds.NOISE_TEMP.value, TestTypeIds.LO_WG_INTEGRITY.value, TestTypeIds.IF_PLATE_NOISE.value):
        noiseTemperature.stop()
        measurementStatus.stopMeasuring()
        return MessageResponse(message = f"{TestTypeIds(cartTest.fkTestType).name} stopped", success = True)
    elif cartTest.fkTestType == TestTypeIds.AMP_STABILITY.value:
        amplitudeStablilty.stop()
        measurementStatus.stopMeasuring()
        return MessageResponse(message = "Amplitude stability stopped", success = True)
    elif cartTest.fkTestType == TestTypeIds.PHASE_STABILITY.value:
        phaseStability.stop()
        measurementStatus.stopMeasuring()
        return MessageResponse(message = "Phase stability stopped", success = True)
    else:
        return MessageResponse(message = f"Nothing to do for test type {cartTest.fkTestType}", success = False)
    
@router.get("/currentTest", response_model = Optional[CartTest])
async def get_Status():
    cartTest = measurementStatus.getMeasuring()
    if not cartTest:
        return None
    elif cartTest.fkTestType == TestTypeIds.BEAM_PATTERN.value:
        if beamScanner.isMeasuring():
            return cartTest
    elif cartTest.fkTestType in (TestTypeIds.NOISE_TEMP.value, TestTypeIds.LO_WG_INTEGRITY.value, TestTypeIds.IF_PLATE_NOISE.value):
        if noiseTemperature.isMeasuring():
            return cartTest
    elif cartTest.fkTestType == TestTypeIds.AMP_STABILITY.value:
        if amplitudeStablilty.isMeasuring():
            return cartTest    
    elif cartTest.fkTestType == TestTypeIds.PHASE_STABILITY.value:
        if phaseStability.isMeasuring():
            return cartTest    
    return None

@router.get("/status", response_model = MeasurementStatus)
async def get_MeasurementStatus():
    return measurementStatus

