from fastapi import APIRouter
from typing import Optional
from schemas.MotorController import *
from schemas.common import SingleBool, SingleFloat
import hardware.BeamScanner as BeamScanner
from Response import MessageResponse

router = APIRouter(prefix="/beamscan")

@router.get("/mc/isconnected", tags=["BeamScan"], response_model = SingleBool)
async def get_isConnected():
    return SingleBool(value = BeamScanner.motorController.isConnected())


