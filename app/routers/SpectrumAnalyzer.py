from fastapi import APIRouter
from schemas.DeviceInfo import DeviceInfo
from hardware.NoiseTemperature import spectrumAnalyzer
from DebugOptions import *

import logging
logger = logging.getLogger("ALMAFE-CTS-Control")

router = APIRouter(prefix="/specanalyzer")

@router.get("/device_info", response_model = DeviceInfo)
async def get_DeviceInfo_SpecAn():
    if SIMULATE:
        resource_name = "simulated spectrum analyzer"
    else:
        resource_name = spectrumAnalyzer.inst.port
    return DeviceInfo(
        resource_name = resource_name,
        is_connected = spectrumAnalyzer.isConnected()
    )
