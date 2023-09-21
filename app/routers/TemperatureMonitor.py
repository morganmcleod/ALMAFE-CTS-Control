from fastapi import APIRouter
import hardware.NoiseTemperature as NoiseTemperature
from CTSDevices.TemperatureMonitor.schemas import Temperatures, DESCRIPTIONS

import logging
logger = logging.getLogger("ALMAFE-CTS-Control")

router = APIRouter(prefix="/tempmonitor")

@router.get("/sensor/{sensor}", response_model = Temperatures)
async def get_TempSensor(sensor: int):
    temp, err = NoiseTemperature.temperatureMonitor.readSingle(sensor)
    return Temperatures(temps = [temp], errors = [err], descriptions = DESCRIPTIONS[sensor])

@router.get("/sensors", response_model = Temperatures)
async def get_TempSensors():
    temps, errors = NoiseTemperature.temperatureMonitor.readAll()
    return Temperatures(temps = temps, errors = errors)
