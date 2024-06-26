from fastapi import APIRouter
from schemas.DeviceInfo import DeviceInfo
from hardware.NoiseTemperature import chopper
from INSTR.Chopper.Band6Chopper import State as ChopperState
from DebugOptions import *

import logging
logger = logging.getLogger("ALMAFE-CTS-Control")

router = APIRouter(prefix="/chopper")

@router.get("/device_info", response_model = DeviceInfo)
async def get_DeviceInfo_Chopper():
    if SIMULATE:
        resource_name = "simulated chopper"
    else:
        resource_name = chopper.inst.port
    return DeviceInfo(
        name = 'chopper',
        resource_name = resource_name,
        is_connected = chopper.isConnected()
    )

@router.get("/state", response_model = ChopperState)
async def get_ChopperState():
    if SIMULATE:
        return ChopperState.TRANSITION
    if chopper.isSpinning():
        return ChopperState.SPINNING
    else:
        return chopper.getState()
