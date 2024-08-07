from fastapi import APIRouter
from Control.schemas.DeviceInfo import DeviceInfo
from hardware.NoiseTemperature import chopper
from INSTR.Chopper.Band6Chopper import ChopperState
from DebugOptions import *

import logging
logger = logging.getLogger("ALMAFE-CTS-Control")

router = APIRouter(prefix="/chopper")

@router.get("/device_info", response_model = DeviceInfo)
async def get_DeviceInfo_Chopper():
    if SIMULATE:
        return DeviceInfo(
            name = 'Chopper',
            resource = 'simulated',
            connected = True
        )
    else:
        return DeviceInfo(
            name = 'Chopper',
            resource = chopper.inst.port,
            connected = chopper.connected()
        )

@router.get("/state", response_model = ChopperState)
async def get_ChopperState():
    if SIMULATE:
        return ChopperState.TRANSITION
    if chopper.isSpinning():
        return ChopperState.SPINNING
    else:
        return chopper.getState()
