from fastapi import APIRouter
from app.hardware.NoiseTemperature import coldLoad
from INSTR.ColdLoad.ColdLoadBase import ColdLoadState, FillMode, FillState
from schemas.common import SingleBool
from schemas.DeviceInfo import DeviceInfo
from DebugOptions import *

import logging
logger = logging.getLogger("ALMAFE-CTS-Control")

router = APIRouter(prefix="/coldload")

@router.get("/device_info", response_model = DeviceInfo)
async def get_DeviceInfo_ColdLoad():
    if SIMULATE:
        resource_name = "simulated cold load controller"
    else:
        resource_name = coldLoad.inst.resource_name
    return DeviceInfo(
        name = 'coldload',
        resource_name = resource_name,
        is_connected = coldLoad.isConnected()
    )

@router.get("/state", response_model = ColdLoadState)
async def get_FillMode():
    mode = coldLoad.getFillMode()
    state = coldLoad.getFillState()
    return ColdLoadState(
        fillMode = mode,
        fillState = state,
        fillModeText = mode.name,
        fillStateText = state.name,
        level = coldLoad.getLevel()
    )
