from fastapi import APIRouter
from hardware.WarmIFPlate import warmIFPlate
from schemas.common import SingleFloat
from Response import MessageResponse

import logging
logger = logging.getLogger("ALMAFE-CTS-Control")

router = APIRouter(prefix="/warmif")

@router.get("/inputswitch", response_model = MessageResponse)
async def getInputSwitch():
    position = warmIFPlate.inputSwitch.getValue()
    return MessageResponse(message = position.name, success = True)

@router.get("/yigfilter", response_model = SingleFloat)
async def getYigFilter():
    return SingleFloat(value = warmIFPlate.yigFilter.getFrequency())

