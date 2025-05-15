import logging
from fastapi import APIRouter
from Controllers.schemas.DeviceInfo import DeviceInfo
import app_MTS2.hardware.PowerDetect
from DebugOptions import *

logger = logging.getLogger("ALMAFE-CTS-Control")
router = APIRouter(prefix="/powerdetect")

@router.get("/device_info", response_model = DeviceInfo)
async def get_device_info_powerdetect():
    return app_MTS2.hardware.PowerDetect.powerDetect.device_info
