import logging
from fastapi import APIRouter
from Controllers.schemas.DeviceInfo import DeviceInfo
import app_MTS2.hardware.PowerDetect
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
        return DeviceInfo.model_validate(app_MTS2.hardware.PowerDetect.spectrumAnalyzer.deviceInfo)
