from fastapi import APIRouter, Response
import app.measProcedure.Stability
amplitudeStablilty = app.measProcedure.Stability.amplitudeStablilty
phaseStability = app.measProcedure.Stability.phaseStability
settingsContainer = app.measProcedure.Stability.settingsContainer
from Measure.Stability.schemas import Settings
from app.database.CTSDB import CTSDB
from DBBand6Cart.TestResultPlots import TestResultPlots
from app.schemas.Response import MessageResponse, ListResponse, prepareListResponse
import logging

logger = logging.getLogger("ALMAFE-CTS-Control")
router = APIRouter(prefix="/stability")

@router.get("/amp/settings", response_model = Settings)
async def get_Settings():
    return settingsContainer.ampStability

@router.post("/amp/settings", response_model = MessageResponse)
async def post_Settings(settings: Settings):
    settingsContainer.ampStability = settings
    settingsContainer.saveSettingsAmpStability()
    return MessageResponse(message = "Updated amplitude stability settings.", success = True)

@router.post("/amp/settings/reset", response_model = MessageResponse)
async def reset_settings():
    settingsContainer.defaultSettingsAmpStability()
    return MessageResponse(message = "Reset amplitude stability settings to defaults.", success = True)

@router.get("/phase/settings", response_model = Settings)
async def get_Settings():
    return settingsContainer.phaseStability

@router.post("/phase/settings", response_model = MessageResponse)
async def post_Settings(settings: Settings):
    settingsContainer.phaseStability = settings
    settingsContainer.saveSettingsPhaseStability()
    return MessageResponse(message = "Updated phase stability settings.", success = True)

@router.post("/phase/settings/reset", response_model = MessageResponse)
async def reset_settings():
    settingsContainer.defaultSettingsPhaseStability()
    return MessageResponse(message = "Reset phase stability settings to defaults.", success = True)

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
