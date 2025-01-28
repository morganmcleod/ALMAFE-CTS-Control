import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
import app_Common.measProcedure.DataDisplay
dataDisplay = app_Common.measProcedure.DataDisplay.dataDisplay
from Measure.MixerTests import ResultsQueue
from Measure.NoiseTemperature.schemas import BiasOptResult
from app_Common.ConnectionManager import ConnectionManager

manager = ConnectionManager()
router = APIRouter(prefix="/display")
logger = logging.getLogger("ALMAFE-CTS-Control")

@router.websocket("/ifsystem_ws")
async def websocket_warmif(websocket: WebSocket):
    await manager.connect(websocket)
    lastCartTest = None
    try:
        while True:
            if not dataDisplay.warmIfData:
                lastCartTest = None
            else:
                if dataDisplay.warmIfData[0].fkCartTest != lastCartTest:
                    lastCartTest = dataDisplay.warmIfData[0].fkCartTest
                    for record in dataDisplay.warmIfData:
                        toSend = jsonable_encoder(record.asDBM())
                        await manager.send(toSend, websocket)
                    
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocketDisconnect: /ifsystem_ws")

@router.websocket("/chopperpower_ws")
async def websocket_chopperpower(websocket: WebSocket):
    await manager.connect(websocket)
    lastIndex = 0
    try:
        while True:
            if not dataDisplay.chopperPowerHistory:
                lastIndex = 0
            else:
                nextIndex = len(dataDisplay.chopperPowerHistory)
                if nextIndex < lastIndex:
                    lastIndex = 0
                records = dataDisplay.chopperPowerHistory[lastIndex:]
                lastIndex = nextIndex
                toSend = jsonable_encoder(records)
                await manager.send(toSend, websocket)
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocketDisconnect: /chopperpower_ws")

@router.websocket("/rawspecan_ws")
async def websocket_rawspecan(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            if dataDisplay.specAnPowerHistory is not None:
                toSend = jsonable_encoder(dataDisplay.specAnPowerHistory)
                await manager.send(toSend, websocket)
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocketDisconnect: /rawspecan_ws")

@router.websocket("/rawnoisetemp_ws")
async def websocket_raw_nt(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            records = dataDisplay.currentNoiseTemp
            if records[0] is not None:
                toSend = jsonable_encoder(records[0])                    
                await manager.send(toSend, websocket)
            if records[1] is not None:
                toSend = jsonable_encoder(records[1])                    
                await manager.send(toSend, websocket)                
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocketDisconnect: /rawnoisetemp_ws")


lastBiasOptResult: BiasOptResult = None

@router.websocket("/biasopt_ws")
async def websocket_biasopt(websocket: WebSocket):
    await manager.connect(websocket)
    global lastBiasOptResult
    try:
        while True:
            if not dataDisplay.biasOptResults:
                lastBiasOptResult = None
            else:
                record = dataDisplay.biasOptResults[-1]
                if record != lastBiasOptResult:
                    lastBiasOptResult = record
                    toSend = jsonable_encoder(record)
                    await manager.send(toSend, websocket)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocketDisconnect: /biasopt_ws")

@router.get("/biasopt", response_model = list[BiasOptResult])
async def get_biasopt():
    global lastBiasOptResult
    if dataDisplay.biasOptResults:
        lastBiasOptResult = dataDisplay.biasOptResults[-1]
        return dataDisplay.biasOptResults
    else:
        lastBiasOptResult = None
        return []

@router.websocket("/yfactor_ws")
async def websocket_yfactor(websocket: WebSocket):
    await manager.connect(websocket)
    lastMsg = None
    try:
        while True:
            if not dataDisplay.yFactorHistory:
                lastMsg = None
            else:
                record = dataDisplay.yFactorHistory[-1]
                if record != lastMsg:
                    lastMsg = record
                    toSend = jsonable_encoder(record)
                    await manager.send(toSend, websocket)
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocketDisconnect: /yfactor_ws")

@router.websocket("/mixertests/iv_curves_ws")
async def websocket_iv_curves(websocket: WebSocket):
    await manager.connect(websocket)
    try:        
        while True:
            try:
                item: ResultsQueue.Item = dataDisplay.ivCurveQueue.get_nowait()
            except Exception as e:
                item = None
            if item is not None:
                await manager.send(jsonable_encoder(item), websocket)
            await asyncio.sleep(0.01)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocketDisconnect: /mixertests/iv_curves_ws")

@router.websocket("/mixertests/magnet_opt_ws")
async def websocket_magnet_opt(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            try:
                item: ResultsQueue.Item = dataDisplay.magnetOptQueue.get_nowait()
                await manager.send(jsonable_encoder(item), websocket)
            except Exception as e:
                pass
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocketDisconnect: /mixertests/magnet_opt_ws")

@router.websocket("/mixertests/mixer_deflux_ws")
async def websocket_mixer_deflux(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocketDisconnect: /mixertests/mixer_deflux_ws")
