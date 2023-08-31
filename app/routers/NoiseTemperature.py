from fastapi import APIRouter
import hardware.NoiseTemperature as NoiseTemperature
from schemas.NoiseTemperature import Temperatures

import logging
logger = logging.getLogger("ALMAFE-CTS-Control")

router = APIRouter(prefix="/noisetemp")

@router.get("/tempsensor/{sensor}", response_model = Temperatures)
def get_TempSensor(sensor: int):
    temp, err = NoiseTemperature.temperatureMonitor.readSingle(sensor)
    return Temperatures(temps = [temp], errors = [err])

@router.get("/tempsensors", response_model = Temperatures)
def get_TempSensors():
    temps, errors = NoiseTemperature.temperatureMonitor.readAll()
    return Temperatures(temps = temps, errors = errors)
