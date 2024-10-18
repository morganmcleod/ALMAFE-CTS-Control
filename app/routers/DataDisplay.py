import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
import measProcedure.DataDisplay
dataDisplay = measProcedure.DataDisplay.dataDisplay
from AMB.schemas.MixerTests import IVCurveResult, MagnetOptResult, DefluxResult
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
        logger.exception("WebSocketDisconnect: /stability/timeseries_ws")

@router.websocket("/mixertests/iv_curves_ws")
async def websocket_iv_curves(websocket: WebSocket):
    # these are local static-like variables that retain their values between calls:
    try:
        lastTimeStamp = websocket_iv_curves.lastTimeStamp
        nextSendIndex = websocket_iv_curves.nextSendIndex
    except:
        lastTimeStamp = websocket_iv_curves.lastTimeStamp = [None, None, None, None]
        nextSendIndex = websocket_iv_curves.nextSendIndex = [0, 0, 0, 0]

    await manager.connect(websocket)
    try:
        while True:
            # cycle through the four mixers:
            curveIndex = 0
            while curveIndex < 4:
                # check for available data:
                curve = dataDisplay.ivCurveResults.curves[curveIndex]
                if len(curve) == 0:
                    curveIndex += 1
                # check if we already sent a curve having the same timestamp:
                elif curve.timeStamp != lastTimeStamp[curveIndex]:
                    # is there new data to send?
                    if len(curve) > nextSendIndex[curveIndex]:
                        if nextSendIndex[curveIndex] == 0:
                            # send an empty result to clear any prevous trace:
                            toSend = IVCurveResult(pol = curve.pol, sis = curve.sis, timeStamp=datetime.now())
                            await manager.send(jsonable_encoder(toSend), websocket)
                        # send the new data:
                        toSend = curve.copy_from_index(nextSendIndex[curveIndex])
                        await manager.send(jsonable_encoder(toSend), websocket)
                    if curve.finished:
                        # save the timestamp so we don't send this one again:
                        lastTimeStamp[curveIndex] = curve.timeStamp
                        nextSendIndex[curveIndex] = 0
                        # for I-V curves we are only ever sending one at a time. 
                        # So go the next curve only when this one's finished:
                        curveIndex += 1
                    else:
                        # save the next index to send on next iteration:
                        nextSendIndex[curveIndex] = len(curve)
                await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /mixertests/iv_curves_ws")


@router.websocket("/mixertests/magnet_opt_ws")
async def websocket_magnet_opt(websocket: WebSocket):
    # these are local static-like variables that retain their values between calls:
    try:
        lastTimeStamp = websocket_magnet_opt.lastTimeStamp
        nextSendIndex = websocket_magnet_opt.nextSendIndex
    except:
        lastTimeStamp = websocket_magnet_opt.lastTimeStamp = [None, None, None, None]
        nextSendIndex = websocket_magnet_opt.nextSendIndex = [0, 0, 0, 0]
    await manager.connect(websocket)
    try:
        while True:
            # cycle through the four mixers:
            curveIndex = 0
            while curveIndex < 4:
                curve = dataDisplay.magnetOptResults.curves[curveIndex]
                # check if we already sent a curve having the same timestamp:
                if curve.timeStamp != lastTimeStamp[curveIndex]:
                    # is there new data to send?                    
                    if len(curve) > nextSendIndex[curveIndex]:
                        if nextSendIndex[curveIndex] == 0:
                            # send an empty result to clear any prevous trace:
                            toSend = MagnetOptResult(pol = curve.pol, sis = curve.sis, timeStamp = datetime.now())
                            await manager.send(jsonable_encoder(toSend), websocket)
                        # send the new data:
                        toSend = curve.copy_from_index(nextSendIndex[curveIndex])
                        await manager.send(jsonable_encoder(toSend), websocket)
                    if curve.finished:
                        # save the timestamp so we don't send this one again:
                        lastTimeStamp[curveIndex] = curve.timeStamp
                        nextSendIndex[curveIndex] = 0                        
                    else:
                        # save the next index to send on next iteration:
                        nextSendIndex[curveIndex] = len(curve)
                # for magnet optimization we are sending all the curves simultaneously. 
                # So go to the next curve after each pass:
                curveIndex += 1
            await asyncio.sleep(0.2)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /mixertests/magnet_opt_ws")

@router.websocket("/mixertests/mixer_deflux_ws")
async def websocket_mixer_deflux(websocket: WebSocket):
    # these are local static-like variables that retain their values between calls:
    try:
        lastTimeStamp = websocket_mixer_deflux.lastTimeStamp
        nextSendIndex = websocket_mixer_deflux.nextSendIndex
    except:
        lastTimeStamp = websocket_mixer_deflux.lastTimeStamp = [None, None]
        nextSendIndex = websocket_mixer_deflux.nextSendIndex = [0, 0]        
    await manager.connect(websocket)
    try:
        while True:
            # cycle through the two polarizations:
            curveIndex = 0
            while curveIndex < 2:
                curve = dataDisplay.defluxResults.curves[curveIndex]
                # check if we already sent a curve having the same timestamp:
                if curve.timeStamp != lastTimeStamp[curveIndex]:
                    # is there new data to send?
                    if len(curve) > nextSendIndex[curveIndex]:
                        if nextSendIndex[curveIndex] == 0:
                            # send an empty result to clear any prevous trace:
                            toSend = DefluxResult(pol = curve.pol, timeStamp = datetime.now())
                            await manager.send(jsonable_encoder(toSend), websocket)
                        # send the new data:
                        toSend = curve.copy_from_index(nextSendIndex[curveIndex])
                        await manager.send(jsonable_encoder(toSend), websocket)
                    if curve.finished:
                        # save the timestamp so we don't send this one again:
                        lastTimeStamp[curveIndex] = curve.timeStamp
                        nextSendIndex[curveIndex] = 0                        
                    else:
                        # save the next index to send on next iteration:
                        nextSendIndex[curveIndex] = len(curve)
                 # for mixers deflux we are sending all the curves simultaneously. 
                 # So go to the next curve after each pass:
                curveIndex += 1
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /mixertests/mixer_deflux_ws")
