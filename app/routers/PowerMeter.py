from fastapi import APIRouter
from schemas.DeviceInfo import DeviceInfo
from hardware.NoiseTemperature import powerMeter
from DebugOptions import *

import logging
logger = logging.getLogger("ALMAFE-CTS-Control")

router = APIRouter(prefix="/powermeter")

@router.get("/device_info", response_model = DeviceInfo)
async def get_DeviceInfo_PowerMeter():
    if SIMULATE:
        resource_name = "simulated power meter"
    else:
        resource_name = powerMeter.inst.port
    return DeviceInfo(
        resource_name = resource_name,
        is_connected = powerMeter.isConnected()
    )
