from fastapi import APIRouter
from app_Common.Response import MessageResponse

from Control.schemas.DeviceInfo import DeviceInfo
import hardware.NoiseTemperature 
chopper = hardware.NoiseTemperature.chopper
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

@router.put("/state", response_model = MessageResponse)
async def put_ChopperState(state: int):
    try:
        _state = ChopperState(state)
    except:
        return MessageResponse(message = f"Invalid chopper state: {state}", success = False)
    if not SIMULATE:
        if _state == ChopperState.OPEN:
            if chopper.openIsHot:
                chopper.gotoHot()
            else:
                chopper.gotoCold()
        elif _state == ChopperState.CLOSED:
            if chopper.openIsHot:
                chopper.gotoCold()
            else:
                chopper.gotoHot()
        elif _state == ChopperState.SPINNING:
            chopper.spin()
    return MessageResponse(message = f"Set chopper state to {_state.name}", success = True)
