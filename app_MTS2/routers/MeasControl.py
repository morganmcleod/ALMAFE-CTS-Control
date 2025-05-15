from fastapi import APIRouter
from typing import Optional
from DBBand6Cart.MixerTests import MixerTest
from app_Common.Response import KeyResponse, MessageResponse
from Measure.Shared.MeasurementStatus import MeasurementStatusModel
import app_MTS2.measProcedure.ScriptRunner
scriptRunner = app_MTS2.measProcedure.ScriptRunner.scriptRunner
from DebugOptions import *

router = APIRouter(prefix="/measure")

@router.put("/start", response_model = KeyResponse)
async def put_Start(testRecord: MixerTest):
    success, msg = scriptRunner.start(testRecord)
    if not success:
        return KeyResponse(key = 0, message = msg, success = False)
    else:
        return KeyResponse(key = testRecord.key, message = msg, success = True)

@router.put("/stop", response_model = MessageResponse)
async def put_Stop():
    success, msg = scriptRunner.stop()
    if not success:
        return MessageResponse(message = msg, success = False)
    else:
        return MessageResponse(message = msg, success = True)
    
@router.get("/current_test", response_model = Optional[MixerTest])
async def get_CurrentTest():
    return scriptRunner.get_mixertest()

@router.get("/status", response_model = MeasurementStatusModel)
async def get_MeasurementStatus():
    return scriptRunner.get_status()

