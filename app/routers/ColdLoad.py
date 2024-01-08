from fastapi import APIRouter
from measProcedure.NoiseTemperature import coldLoad
from CTSDevices.ColdLoad.ColdLoadBase import ColdLoadState, FillMode, FillState

import logging
logger = logging.getLogger("ALMAFE-CTS-Control")

router = APIRouter(prefix="/coldload")

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
