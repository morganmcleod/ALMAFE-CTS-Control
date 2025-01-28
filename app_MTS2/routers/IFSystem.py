import logging
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from Controllers.schemas.DeviceInfo import DeviceInfo
from Controllers.IFSystem.Interface import InputSelect
from app_Common.schemas.common import SingleFloat, SingleInt
from app_Common.Response import MessageResponse
from DebugOptions import *

import app_MTS2.hardware.IFSystem
ifSystem = app_MTS2.hardware.IFSystem.ifSystem

logger = logging.getLogger("ALMAFE-CTS-Control")
router = APIRouter(prefix="/ifsystem")

@router.get("/device_info", response_model = DeviceInfo)
async def get_device_info():
    return ifSystem.device_info

@router.get("/input_select", response_class = JSONResponse)
async def get_input_select():
    return JSONResponse(content = ifSystem.input_select.value)

@router.post('/input_select', response_model = MessageResponse)
async def set_input_select(value: int | str):
    try:
        ifSystem.input_select = InputSelect(int(value))
        return MessageResponse(message = f"IF System input_select set to {ifSystem.input_select.name}", success = True)
    except:
        return MessageResponse(message = f"Invalid value for input_select: {value}", success = False)

@router.get("/frequency", response_model = SingleFloat)
async def get_frequency():
    return SingleFloat(value = ifSystem.frequency)

@router.post("/frequency", response_model = MessageResponse)
async def setYigFilter(value: float):
    try:
        ifSystem.frequency = value
        return MessageResponse(message = f"Set IF System frequency to {value} GHz", success = True)
    except:
        return MessageResponse(message = f"Failed setting IF System frequency to {value} GHz", success = False)

@router.get("/attenuation", response_model = SingleInt)
async def get_attenuation():
    return SingleInt(value = ifSystem.attenuation)

@router.post("/attenuation", response_model = MessageResponse)
async def setAtten(value: int):
    try:
        ifSystem.attenuation = value
        return MessageResponse(message = f"Set IF System attenuation to {value} dB", success = True)
    except:
        return MessageResponse(message = f"Failed setting IF System attenuation to {value} dB", success = False)
