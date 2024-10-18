from fastapi import APIRouter
from typing import Optional
from DBBand6Cart.CartTests import CartTest
from app.schemas.Response import KeyResponse, MessageResponse
from Measure.Shared.MeasurementStatus import MeasurementStatusModel
import measProcedure.ScriptRunner
scriptRunner = measProcedure.ScriptRunner.scriptRunner
from DebugOptions import *

router = APIRouter(prefix="/measure")

@router.put("/start", response_model = KeyResponse)
async def put_Start(cartTest:CartTest):
    success, msg = scriptRunner.start(cartTest)
    if not success:
        return KeyResponse(key = 0, message = msg, success = False)
    else:
        return KeyResponse(key = cartTest.key, message = msg, success = True)

@router.put("/stop", response_model = MessageResponse)
async def put_Stop():
    success, msg = scriptRunner.stop()
    if not success:
        return MessageResponse(message = msg, success = False)
    else:
        return MessageResponse(message = msg, success = True)
    
@router.get("/current_test", response_model = Optional[CartTest])
async def get_CurrentTest():
    return scriptRunner.get_carttest()

@router.get("/status", response_model = MeasurementStatusModel)
async def get_MeasurementStatus():
    return scriptRunner.get_status()

