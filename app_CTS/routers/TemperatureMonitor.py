import logging
from fastapi import APIRouter
import hardware.NoiseTemperature
temperatureMonitor = hardware.NoiseTemperature.temperatureMonitor
from INSTR.TemperatureMonitor.schemas import Temperatures, DESCRIPTIONS
from Controllers.schemas.DeviceInfo import DeviceInfo
from DebugOptions import *

logger = logging.getLogger("ALMAFE-CTS-Control")
router = APIRouter(prefix="/tempmonitor")

@router.get("/device_info", response_model = DeviceInfo)
async def get_DeviceInfo_TempMonitor():
    if SIMULATE:
        return DeviceInfo(
            name = 'temperature monitor',
            resource = 'simulated',
            connected = True
        )
        resource = " "
    else:
        return DeviceInfo(
            name = 'temperature monitor',
            resource = temperatureMonitor.inst.resource,
            connected = temperatureMonitor.connected()
        )

@router.get("/sensor/{sensor}", response_model = Temperatures)
async def get_TempSensor(sensor: int):
    temp, err = temperatureMonitor.readSingle(sensor)
    return Temperatures(temps = [temp], errors = [err], descriptions = DESCRIPTIONS[sensor])

@router.get("/sensors", response_model = Temperatures)
async def get_TempSensors():
    temps, errors = temperatureMonitor.readAll()
    return Temperatures(temps = temps, errors = errors)
