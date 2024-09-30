import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from app.measProcedure.DataDisplay import dataDisplay
from .ConnectionManager import ConnectionManager

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
        logger.exception("WebSocketDisconnect: /ifsystem_ws")

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
        logger.exception("WebSocketDisconnect: /chopperpower_ws")

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
        logger.exception("WebSocketDisconnect: /rawspecan_ws")

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
        logger.exception("WebSocketDisconnect: /rawnoisetemp_ws")

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
        logger.exception("WebSocketDisconnect: /yfactor_ws")

@router.websocket("/stability/timeseries_ws")
async def websocket_amp_timeseries_push(websocket: WebSocket):
    await manager.connect(websocket)
    lastMsg = None
    try:
        while True:
            if not dataDisplay.stabilityHistory:
                lastMsg = None
            else:
                record = dataDisplay.stabilityHistory[-1]
                if record != lastMsg:
                    lastMsg = record
                    toSend = jsonable_encoder(record)
                    await manager.send(toSend, websocket) 
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /amp/timeseries_ws")
