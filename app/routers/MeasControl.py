from fastapi import APIRouter
from typing import Optional
from Response import KeyResponse, MessageResponse
from DBBand6Cart.CartTests import CartTest, CartTests
from DBBand6Cart.TestTypes import TestTypeIds
from .Database import CTSDB
from socket import getfqdn

import hardware.BeamScanner as BeamScanner
import hardware.Measuring as Measuring
from DebugOptions import *

import logging
logger = logging.getLogger("ALMAFE-CTS-Control")

router = APIRouter(prefix="/measure")

@router.put("/start", response_model = KeyResponse)
async def put_Start(cartTest:CartTest):
    cartTestsDb = CartTests(driver = CTSDB())
    cartTest.testSysName = getfqdn()
    if not SIMULATE:
        cartTestId = cartTestsDb.create(cartTest)
    else:
        cartTestId = 1
    if cartTestId:
        if cartTest.fkTestType == TestTypeIds.BEAM_PATTERN.value:
            BeamScanner.beamScanner.keyCartTest = cartTestId
            BeamScanner.beamScanner.start()
            Measuring.measuring.setMeasuring(cartTest)
            return KeyResponse(key = cartTestId, message = "Beam scans started", success = True)        
    else:
        return KeyResponse(key = 0, message = "Failed creating CartTest record", success = False)

@router.put("/stop", response_model = MessageResponse)
async def put_Stop():
    cartTest = Measuring.measuring.getMeasuring()
    if cartTest:
        if cartTest.fkTestType == TestTypeIds.BEAM_PATTERN.value:
            BeamScanner.beamScanner.stop()
            Measuring.measuring.stopMeasuring()
            return MessageResponse(message = "Beam scans stopped", success = True)
        
@router.get("/status", response_model = Optional[CartTest])
async def get_Status():
    return Measuring.measuring.getMeasuring()
