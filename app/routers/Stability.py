from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Response
from fastapi.encoders import jsonable_encoder
from typing import List, Tuple, Optional
from schemas.common import SingleBool, SingleFloat
from app.measProcedure.Stability import amplitudeStablilty, phaseStability
from app.measProcedure.MeasurementStatus import measurementStatus
from AmpPhaseDataLib.Constants import DataSource, PlotEl, SpecLines
from AmpPhaseDataLib.TimeSeriesAPI import TimeSeriesAPI
from AmpPhasePlotLib.PlotAPI import PlotAPI
from Measure.Stability.schemas import Settings
from AmpPhaseDataLib.TimeSeries import TimeSeries
from app.database.CTSDB import CTSDB
from app.schemas.Stability import StabilityPlot
from DBBand6Cart.AmplitudeStability import AmplitudeStability as AmplitudeStability_DB
from DBBand6Cart.PhaseStability import PhaseStability as PhaseStability_DB
from DBBand6Cart.TestResultPlots import TestResultPlots
from .ConnectionManager import ConnectionManager
from app.schemas.Response import MessageResponse, ListResponse, prepareListResponse
import asyncio
import logging
import json
from datetime import datetime

logger = logging.getLogger("ALMAFE-CTS-Control")

router = APIRouter(prefix="/stability")
manager = ConnectionManager()

@router.websocket("/amp/timeseries_ws")
async def websocket_amp_timeseries_push(websocket: WebSocket):
    await manager.connect(websocket)
    lastMessageId = None
    lastTimeStamp = None
    try:
        while True:
            doSend = False
            ts = amplitudeStablilty.getTimeSeries(latestOnly = True)
            if ts.tsId != lastMessageId:
                lastMessageId = ts.tsId
                doSend = True
            elif ts.timeStamps and ts.timeStamps[0] != lastTimeStamp:
                lastTimeStamp = ts.timeStamps[0]
                doSend = True
            if doSend:
                ts = jsonable_encoder(ts)
                await manager.send(ts, websocket)                
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /amp/timeseries_ws")

@router.websocket("/phase/timeseries_ws")
async def websocket_phase_timeseries_push(websocket: WebSocket):
    await manager.connect(websocket)
    lastMessageId = None
    lastTimeStamp = None
    try:
        while True:
            doSend = False
            ts = phaseStability.getTimeSeries(latestOnly = True)
            if ts.tsId != lastMessageId:
                lastMessageId = ts.tsId
                doSend = True
            elif ts.timeStamps and ts.timeStamps[0] != lastTimeStamp:
                lastTimeStamp = ts.timeStamps[0]
                doSend = True
            if doSend:
                ts = jsonable_encoder(ts)
                await manager.send(ts, websocket)                
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /phase/timeseries_ws")

@router.get("/amp/timeseries", response_model = TimeSeries)
async def get_TimeSeries(first: int, last: Optional[int] = -1, targetLength: Optional[int] = None):
    return amplitudeStablilty.getTimeSeries(first, last, targetLength = targetLength)

@router.get("/phase/timeseries", response_model = TimeSeries)
async def get_TimeSeries(first: int, last: Optional[int] = -1, targetLength: Optional[int] = None):
    return phaseStability.getTimeSeries(first, last, targetLength = targetLength)

@router.get("/amp/settings", response_model = Settings)
async def get_Settings():
    return amplitudeStablilty.settings

@router.get("/phase/settings", response_model = Settings)
async def get_Settings():
    return phaseStability.settings

@router.post("/amp/settings", response_model = MessageResponse)
async def post_Settings(settings: Settings):
    amplitudeStablilty.settings = settings
    return MessageResponse(message = "Updated amplitude stability settings.", success = True)

@router.post("/phase/settings", response_model = MessageResponse)
async def post_Settings(settings: Settings):
    phaseStability.settings = settings
    return MessageResponse(message = "Updated phase stability settings.", success = True)

@router.get("/amp/timeseries/list", response_model = ListResponse)
async def get_TimeSeriesIds():
    items = amplitudeStablilty.timeSeriesList
    return prepareListResponse(items)

@router.get("/phase/timeseries/list", response_model = ListResponse)
async def get_TimeSeriesIds():
    items = phaseStability.timeSeriesList
    return prepareListResponse(items)

@router.get("/amp/timeseries/plot/{tsId}")
async def get_AmpTimeSeriesPlot(tsId: int):
    result = None
    info = next((x for x in amplitudeStablilty.timeSeriesList if x.key == tsId), None)
    if info and info.timeSeriesPlot:
        DB = TestResultPlots(driver = CTSDB())
        result = DB.read(info.timeSeriesPlot)
    if result:
        return Response(content = result[0].plotBinary, media_type=result[0].contentType)
    else:
        return Response(content = b"")

@router.get("/phase/timeseries/plot/{tsId}")
async def get_PhaseTimeSeriesPlot(tsId: int):
    result = None
    info = next((x for x in phaseStability.timeSeriesList if x.key == tsId), None)
    if info and info.timeSeriesPlot:
        DB = TestResultPlots(driver = CTSDB())
        result = DB.read(info.timeSeriesPlot)
    if result:
        return Response(content = result[0].plotBinary, media_type=result[0].contentType)
    else:
        return Response(content = b"")

@router.get("/amp/allan/plot/{tsId}")
async def get_AmpAllanPlot(tsId: int):
    result = None
    info = next((x for x in amplitudeStablilty.timeSeriesList if x.key == tsId), None)
    if info and info.allanPlot:
        DB = TestResultPlots(driver = CTSDB())
        result = DB.read(info.allanPlot)
    if result:
        return Response(content = result[0].plotBinary, media_type=result[0].contentType)
    else:
        return Response(content = b"")

@router.get("/phase/allan/plot/{tsId}")
async def get_PhaseAllanPlot(tsId: int):
    result = None
    info = next((x for x in phaseStability.timeSeriesList if x.key == tsId), None)
    if info and info.allanPlot:
        DB = TestResultPlots(driver = CTSDB())
        result = DB.read(info.allanPlot)
    if result:
        return Response(content = result[0].plotBinary, media_type=result[0].contentType)
    else:
        return Response(content = b"")
