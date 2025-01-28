import logging
from fastapi import APIRouter
from Control.schemas.DeviceInfo import DeviceInfo
import hardware.PowerDetect
from DebugOptions import *

logger = logging.getLogger("ALMAFE-CTS-Control")
router = APIRouter(prefix="/powerdetect")

@router.get("/device_info", response_model = DeviceInfo)
async def get_device_info_powerdetect():
    return hardware.PowerDetect.powerDetect.device_info
