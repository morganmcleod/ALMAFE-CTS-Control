import logging
from fastapi import APIRouter
from Control.schemas.DeviceInfo import DeviceInfo
import hardware.PowerDetect
from DebugOptions import *

logger = logging.getLogger("ALMAFE-CTS-Control")
router = APIRouter(prefix="/specanalyzer")

@router.get("/device_info", response_model = DeviceInfo)
async def get_DeviceInfo_SpecAn():    
    if SIMULATE:
        return DeviceInfo(
            name = 'spectrum analyzer',
            resource = 'simulated',
            connected = True
        )
    else:
        return DeviceInfo.model_validate(hardware.PowerDetect.spectrumAnalyzer.deviceInfo)
