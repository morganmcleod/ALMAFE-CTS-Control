from fastapi import APIRouter
from app.hardware.NoiseTemperature import temperatureMonitor
from CTSDevices.TemperatureMonitor.schemas import Temperatures, DESCRIPTIONS
from schemas.common import SingleBool
from schemas.DeviceInfo import DeviceInfo
from DebugOptions import *

import logging
logger = logging.getLogger("ALMAFE-CTS-Control")

router = APIRouter(prefix="/tempmonitor")

@router.get("/device_info", response_model = DeviceInfo)
async def get_DeviceInfo_TempMonitor():
    if SIMULATE:
        resource_name = "simulated temperature monitor"
    else:
        resource_name = temperatureMonitor.inst.resource_name
    return DeviceInfo(
        name = 'tempmonitor',
        resource_name = resource_name,
        is_connected = temperatureMonitor.isConnected()
    )

@router.get("/sensor/{sensor}", response_model = Temperatures)
async def get_TempSensor(sensor: int):
    temp, err = temperatureMonitor.readSingle(sensor)
    return Temperatures(temps = [temp], errors = [err], descriptions = DESCRIPTIONS[sensor])

@router.get("/sensors", response_model = Temperatures)
async def get_TempSensors():
    temps, errors = temperatureMonitor.readAll()
    return Temperatures(temps = temps, errors = errors)
