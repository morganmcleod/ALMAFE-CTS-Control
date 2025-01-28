import logging
from fastapi import APIRouter
import app_MTS2.hardware.NoiseTemperature
coldLoad = app_MTS2.hardware.NoiseTemperature.coldLoad
from INSTR.ColdLoad.ColdLoadBase import ColdLoadState
from Controllers.schemas.DeviceInfo import DeviceInfo
from DebugOptions import *

logger = logging.getLogger("ALMAFE-CTS-Control")
router = APIRouter(prefix="/coldload")

@router.get("/device_info", response_model = DeviceInfo)
async def get_DeviceInfo_ColdLoad():
    try:
        return DeviceInfo(
            name = 'Cold load controller',
            resource = coldLoad.inst.resource,
            connected = coldLoad.connected()
        )
    except:
        return DeviceInfo(
            name = 'Cold load controller',
            resource = 'simulated',
            connected = coldLoad.connected()
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
