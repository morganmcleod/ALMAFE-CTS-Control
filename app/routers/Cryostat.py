from fastapi import APIRouter
from schemas.CryostatTemperatures import CryostatTemperatures
import hardware.TemperatureMonitor as temperatureMonitor

router = APIRouter(prefix="/cryostat")

@router.get("/tempsensor/{sensor}", response_model = CryostatTemperatures)
def get_TempSensor(sensor: int):
    temp, err = temperatureMonitor.temperatureMonitor.readSingle(sensor)
    return CryostatTemperatures(temps = [temp], errors = [err])

@router.get("/tempsensors", response_model = CryostatTemperatures)
def get_TempSensors():
    temps, errors = temperatureMonitor.temperatureMonitor.readAll()
    return CryostatTemperatures(temps = temps, errors = errors)

