from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from typing import List, Optional
from app.measProcedure.NoiseTemperature import noiseTemperature, coldLoad, yFactor
from app.measProcedure.MeasurementStatus import measurementStatus
from Measure.NoiseTemperature.schemas import TestSteps, CommonSettings, WarmIFSettings, NoiseTempSettings, YFactorSample
from CTSDevices.ColdLoad.AMI1720 import AMI1720, FillMode
from schemas.common import SingleFloat
from Response import MessageResponse
from .ConnectionManager import ConnectionManager
from DBBand6Cart.schemas.WarmIFNoise import WarmIFNoise
import asyncio

import logging
logger = logging.getLogger("ALMAFE-CTS-Control")

router = APIRouter(prefix="/noisetemp")
manager = ConnectionManager()

@router.websocket("/warmif_ws")
async def websocket_warmif(websocket: WebSocket):
    await manager.connect(websocket)
    lastId = 0            
    try:
        while True:
            if not noiseTemperature.warmIfNoise.rawData:
                lastId = 0
            else:
                record = noiseTemperature.warmIfNoise.rawData[-1]
                if record.key != lastId:
                    lastId = record.key
                    toSend = jsonable_encoder(record.asDBM())
                    await manager.send(toSend, websocket)
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /warmif_ws")

@router.websocket("/chopperpower_ws")
async def websocket_warmif(websocket: WebSocket):
    await manager.connect(websocket)
    lastIndex = 0
    try:
        while True:
            if not noiseTemperature.noiseTemp.chopperPowerHistory:
                lastIndex = 0
            else:
                nextIndex = len(noiseTemperature.noiseTemp.chopperPowerHistory)
                if nextIndex < lastIndex:
                    lastIndex = 0
                records = noiseTemperature.noiseTemp.chopperPowerHistory[lastIndex:]
                lastIndex = nextIndex
                toSend = jsonable_encoder(records)
                await manager.send(toSend, websocket)
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /chopperpower_ws")

@router.websocket("/rawnoisetemp_ws")
async def websocket_warmif(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            if noiseTemperature.noiseTemp.rawDataRecords is not None:
                toSend = jsonable_encoder(noiseTemperature.noiseTemp.rawDataRecords)
                await manager.send(toSend, websocket)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /rawnoisetemp_ws")

@router.get("/warmif_raw", response_model = List[WarmIFNoise])
async def get_warmif_raw(first: int, last: Optional[int] = -1):
    meas = noiseTemperature.warmIfNoise
    if meas and meas.rawData:
        return meas.rawData

@router.get("/teststeps", response_model = TestSteps)
async def get_TestSteps():
    return noiseTemperature.testSteps

@router.post("/teststeps",  response_model = MessageResponse)
async def put_TestSteps(testSteps: TestSteps):
    noiseTemperature.testSteps = testSteps
    return MessageResponse(message = "Updated Test Steps " + testSteps.getText(), success = True)

@router.get("/settings", response_model = CommonSettings)
async def get_TestSettings():
    return noiseTemperature.commonSettings

@router.post("/settings",  response_model = MessageResponse)
async def put_Settings(settings: CommonSettings):
    noiseTemperature.updateSettings(settings)
    return MessageResponse(message = "Updated Settings", success = True)

@router.get("/wifsettings", response_model = WarmIFSettings)
async def get_WifSettings():
    return noiseTemperature.warmIFSettings

@router.post("/wifsettings",  response_model = MessageResponse)
async def put_NtSettings(settings: WarmIFSettings):
    noiseTemperature.updateSettings(warmIFSettings = settings)
    return MessageResponse(message = "Updated Warm IF Noise Settings", success = True)

@router.get("/ntsettings", response_model = NoiseTempSettings)
async def get_NtSettings():
    return noiseTemperature.noiseTempSetings

@router.post("/ntsettings",  response_model = MessageResponse)
async def put_NtSettings(settings: NoiseTempSettings):
    noiseTemperature.updateSettings(noiseTempSetings = settings)
    return MessageResponse(message = "Updated Noise Temp Settings", success = True)

@router.get("/lowgsettings", response_model = NoiseTempSettings)
async def get_NtSettings():
    return noiseTemperature.loWgIntegritySettings

@router.post("/lowgsettings",  response_model = MessageResponse)
async def put_NtSettings(settings: NoiseTempSettings):
    noiseTemperature.updateSettings(loWgIntegritySettings = settings)
    return MessageResponse(message = "Updated LO WG Settings", success = True)

@router.get("/coldload/level", response_model = SingleFloat)
async def get_ColdLoadLevel():
    level, err = coldLoad.checkLevel()
    return SingleFloat(value = level)

@router.post("/coldload/fillmode", response_model = MessageResponse)
async def put_ColdLoadFillMode(fillMode_: int):
    try:
        fillMode = FillMode(fillMode_)
        coldLoad.setFillMode(fillMode)
        return MessageResponse(message = f"Cold load: Set fill mode {fillMode}", success = True)
    except:
        return MessageResponse(message = "Cold load: Failed set fill mode", success = False)
        
@router.post("/coldload/startfill", response_model = MessageResponse)
async def put_ColdLoadStartFill():
    coldLoad.startFill()
    return MessageResponse(message = "Cold load: Fill started", success = True)

@router.post("/coldload/stopfill", response_model = MessageResponse)
async def put_ColdLoadStopFill():
    coldLoad.stopFill()
    return MessageResponse(message = "Cold load: Fill stopped", success = True)

@router.websocket("/yfactor_ws")
async def websocket_yfactor(websocket: WebSocket):
    await manager.connect(websocket)
    lastMsg = None
    try:
        while True:
            if not yFactor.isMeasuring() or not yFactor.yFactorHistory:
                lastMsg = None
            else:
                record = yFactor.yFactorHistory[-1]
                if record != lastMsg:
                    lastMsg = record
                    toSend = jsonable_encoder(record)
                    await manager.send(toSend, websocket)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /yfactor_ws")

@router.post("/yfactor/start", response_model = MessageResponse)
async def put_YFactorStart():
    yFactor.start()
    return MessageResponse(message = "Y-factor started", success = True)

@router.post("/yfactor/stop", response_model = MessageResponse)
async def put_YFactorStop():
    yFactor.stop()
    return MessageResponse(message = "Y-factor stopped", success = True)

@router.get("/yfactor/now", response_model = YFactorSample)
async def get_YFactorNow():
    if not yFactor.yFactorHistory:
        return YFactorSample(Y = 0, TRx = 0)
    else:
        return yFactor.yFactorHistory[-1]
