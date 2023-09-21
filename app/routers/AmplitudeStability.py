from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from typing import List, Tuple, Optional
from schemas.common import SingleBool, SingleFloat
import measProcedure.AmplitudeStability as ASMeasProcedure
amplitudeStablilty = ASMeasProcedure.amplitudeStablilty
import app.measProcedure.MeasurementStatus as MeasurementStatus
from AmpPhaseDataLib.Constants import DataSource, PlotEl, SpecLines
from AmpPhaseDataLib.TimeSeriesAPI import TimeSeriesAPI
from AmpPhasePlotLib.PlotAPI import PlotAPI
from Measure.Stability.schemas import Settings
from AmpPhaseDataLib.TimeSeries import TimeSeries
from app.database.CTSDB import CTSDB
from app.schemas.Stability import StabilityPlot
from DBBand6Cart.AmplitudeStability import AmplitudeStability as AmplitudeStability_DB
from .ConnectionManager import ConnectionManager
from Response import MessageResponse, ListResponse, prepareListResponse
import asyncio
import logging
import json
from datetime import datetime

logger = logging.getLogger("ALMAFE-CTS-Control")

router = APIRouter(prefix="/ampstability")
manager = ConnectionManager()

@router.websocket("/timeseries_ws")
async def websocket_timeseries_push(websocket: WebSocket):
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
        logger.exception("WebSocketDisconnect: /timeseries_ws")

@router.get("/timeseries", response_model = TimeSeries)
async def get_TimeSeries(first: int, last: Optional[int] = -1, targetLength: Optional[int] = None):
    return amplitudeStablilty.getTimeSeries(first, last, targetLength = targetLength)

@router.get("/settings", response_model = Settings)
async def get_Settings():
    return amplitudeStablilty.settings

@router.post("/settings", response_model = MessageResponse)
async def post_Settings(settings: Settings):
    amplitudeStablilty.settings = settings
    return MessageResponse(message = "Updated amplitude stability settings.", success = True)

@router.get("/timeseries/list", response_model = ListResponse)
async def get_TimeSeriesIds():
    items = amplitudeStablilty.timeSeriesList
    return prepareListResponse(items)

@router.get("/allanvar/{tsId}", response_model = Optional[StabilityPlot])
async def get_Allanvar(tsId: int):
    timeSeriesInfo = next((x for x in amplitudeStablilty.timeSeriesList if x.key == tsId), None)
    if not timeSeriesInfo:
        return None

    try:
        get_Allanvar.DB
    except:
        get_Allanvar.DB = AmplitudeStability_DB(driver = CTSDB())
    rows = get_Allanvar.DB.read(fkRawData = tsId)
    
    return StabilityPlot(
        key = tsId,
        fkCartTest = amplitudeStablilty.cartTest.key,
        fkTestType = amplitudeStablilty.cartTest.fkTestType,
        timeStamp = timeSeriesInfo.timeStamp,
        freqLO = timeSeriesInfo.freqLO,
        pol = timeSeriesInfo.pol,
        sideband = timeSeriesInfo.sideband,
        x = [row.time for row in rows],
        y = [row.allanVar for row in rows],        
        yError = [row.errorBar for row in rows],
    )

