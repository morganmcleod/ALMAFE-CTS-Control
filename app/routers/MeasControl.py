from fastapi import APIRouter
from typing import Optional
from Response import KeyResponse, MessageResponse
from DBBand6Cart.CartTests import CartTest
from DBBand6Cart.TestTypes import TestTypeIds
from socket import getfqdn

import hardware.BeamScanner as BeamScanner
import hardware.NoiseTemperature as NoiseTemperature
import hardware.Measuring as Measuring
from DebugOptions import *

import logging
logger = logging.getLogger("ALMAFE-CTS-Control")

router = APIRouter(prefix="/measure")

@router.put("/start", response_model = KeyResponse)
async def put_Start(cartTest:CartTest):
    cartTest.testSysName = getfqdn()
    if cartTest.fkTestType == TestTypeIds.BEAM_PATTERN.value:
        cartTestId = BeamScanner.beamScanner.start(cartTest)
        Measuring.measuring.setMeasuring(cartTest)
        return KeyResponse(key = cartTestId, message = "Beam scans started", success = True)
    if cartTest.fkTestType in (TestTypeIds.NOISE_TEMP.value, TestTypeIds.LO_WG_INTEGRITY, TestTypeIds.IF_PLATE_NOISE):
        cartTestId = NoiseTemperature.noiseTemperature.start(cartTest)
        Measuring.measuring.setMeasuring(cartTest)
        return KeyResponse(key = cartTestId, message = "Noise temp / LOWG integrity / Warm IF noise started", success = True)
    else:
        return KeyResponse(key = 0, message = f"Nothing to do for test type {cartTest.fkTestType}", success = False)

@router.put("/stop", response_model = MessageResponse)
async def put_Stop():
    cartTest = Measuring.measuring.getMeasuring()
    if cartTest:
        if cartTest.fkTestType == TestTypeIds.BEAM_PATTERN.value:
            BeamScanner.beamScanner.stop()
            Measuring.measuring.stopMeasuring()
            return MessageResponse(message = "Beam scans stopped", success = True)
        elif cartTest.fkTestType == TestTypeIds.IF_PLATE_NOISE.value:
            NoiseTemperature.warmIFNoise.stop()
            Measuring.measuring.stopMeasuring()
            return MessageResponse(message = "Warm IF noise stopped", success = True)
        
@router.get("/status", response_model = Optional[CartTest])
async def get_Status():
    return Measuring.measuring.getMeasuring()
