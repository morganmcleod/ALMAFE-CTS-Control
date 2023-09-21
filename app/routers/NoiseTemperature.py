from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Optional
import measProcedure.NoiseTemperature as NoiseTemperature
from Measure.NoiseTemperature.schemas import TestSteps, CommonSettings, WarmIFSettings, NoiseTempSettings
from Response import MessageResponse
from .ConnectionManager import ConnectionManager
from DBBand6Cart.schemas.WarmIFNoise import WarmIFNoise
import asyncio

import logging
logger = logging.getLogger("ALMAFE-CTS-Control")

router = APIRouter(prefix="/noisetemp")
manager = ConnectionManager()

@router.websocket("/warmif_ws")
async def websocket_warmif_request(websocket: WebSocket):
    await manager.connect(websocket)
    lastId = 0            
    try:
        while True:
            meas = NoiseTemperature.noiseTemperature.warmIfNoise
            if meas and meas.rawData:
                record = meas.rawData[-1]
                if record.id != lastId:
                    lastId = record.id                 
                    await manager.send(record.dict(), websocket)
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /warmif_ws")

@router.get("/warmif_raw", response_model = List[WarmIFNoise])
async def get_warmif_raw(first: int, last: Optional[int] = -1):
    meas = NoiseTemperature.noiseTemperature.warmIfNoise
    if meas and meas.rawData:
        return meas.rawData

@router.get("/teststeps", response_model = TestSteps)
async def get_TestSteps():
    return NoiseTemperature.noiseTemperature.testSteps

@router.post("/teststeps",  response_model = MessageResponse)
async def put_TestSteps(testSteps: TestSteps):
    NoiseTemperature.noiseTemperature.testSteps = testSteps
    return MessageResponse(message = "Updated Test Steps", success = True)

@router.get("/settings", response_model = CommonSettings)
async def get_TestSettings():
    return NoiseTemperature.noiseTemperature.commonSettings

@router.post("/settings",  response_model = MessageResponse)
async def put_Settings(settings: CommonSettings):
    NoiseTemperature.noiseTemperature.commonSettings = settings
    return MessageResponse(message = "Updated Settings", success = True)

@router.get("/wifsettings", response_model = WarmIFSettings)
async def get_WifSettings():
    return NoiseTemperature.noiseTemperature.warmIFSettings

@router.post("/wifsettings",  response_model = MessageResponse)
async def put_NtSettings(settings: WarmIFSettings):
    NoiseTemperature.noiseTemperature.warmIFSettings = settings
    return MessageResponse(message = "Updated Warm IF Noise Settings", success = True)

@router.get("/ntsettings", response_model = NoiseTempSettings)
async def get_NtSettings():
    return NoiseTemperature.noiseTemperature.noiseTempSetings

@router.post("/ntsettings",  response_model = MessageResponse)
async def put_NtSettings(settings: NoiseTempSettings):
    NoiseTemperature.noiseTemperature.noiseTempSetings = settings
    return MessageResponse(message = "Updated Noise Temp Settings", success = True)

@router.get("/lowgsettings", response_model = NoiseTempSettings)
async def get_NtSettings():
    return NoiseTemperature.noiseTemperature.loWgIntegritySettings

@router.post("/lowgsettings",  response_model = MessageResponse)
async def put_NtSettings(settings: NoiseTempSettings):
    NoiseTemperature.noiseTemperature.loWgIntegritySettings = settings
    return MessageResponse(message = "Updated LO WG Settings", success = True)