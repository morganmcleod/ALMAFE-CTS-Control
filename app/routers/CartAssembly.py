import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import hardware.FEMC as FEMC
from app.schemas.Response import MessageResponse
from .ConnectionManager import ConnectionManager
from AMB.CCADevice import DefluxStatus
from Control.CartAssembly import IVCurveResults

logger = logging.getLogger("ALMAFE-CTS-Control")
router = APIRouter(prefix="/cartassy")
manager = ConnectionManager()

@router.websocket("/sis/current_ws")
async def websocket_sis_current(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            if FEMC.cartAssembly.autoLOPol is not None:
                sis = FEMC.ccaDevice.getSIS(pol = FEMC.cartAssembly.autoLOPol, sis=1, averaging=2, nDigits = 1, takeAbs = True)
                await manager.send(sis, websocket)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /cartassy/sis/current_ws")

@router.websocket("/auto_lo/current_ws")
async def websocket_sis_current(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            if FEMC.cartAssembly.autoLOPol is not None:
                sis = FEMC.ccaDevice.getSIS(pol = FEMC.cartAssembly.autoLOPol, sis=1, averaging=2, nDigits = 1, takeAbs = True)
                await manager.send(sis, websocket)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /cartassy/auto_lo/current_ws")

@router.put("/auto_lo", response_model = MessageResponse)
async def put_AutoLOPower(pol: int):
    pol0 = True if pol in (-1, 0) else False
    pol1 = True if pol in (-1, 1) else False

    if not FEMC.cartAssembly.autoLOPower(pol0, pol1, onThread = True):
        return MessageResponse(message = f"Auto LO power failed pol={pol}", success = False)
    else:
        return MessageResponse(message = f"Setting auto LO power for pol={pol}...", success = True)

@router.put("/mixersdeflux", response_model = MessageResponse)
async def put_MixerDeflux(pol: int, iMagMax: float = 40.0, iMagStep: float = 1.0):
    pol0 = True if pol in (-1, 0) else False
    pol1 = True if pol in (-1, 1) else False
    
    if not FEMC.cartAssembly.mixersDeflux(pol0, pol1, iMagMax, iMagStep, onThread = True):
        return MessageResponse(message = f"Mixers deflux failed for pol={pol}", success = False)
    else:
        return MessageResponse(message = f"Mixers deflux started for pol={pol}...", success = True)

@router.get("/mixersdeflux", response_model = DefluxStatus)
async def get_MixerDeflux():
    return FEMC.cartAssembly.ccaDevice.defluxStatus


@router.put("/ivcurve", response_model = MessageResponse)
async def sis_IVCurve(pol0: bool = True, pol1: bool = True, sis1: bool = True, sis2: bool = True,
                      VjLow: float = None, VjHigh: float = None, VjStep: float = None):
    FEMC.cartAssembly.IVCurve(pol0, pol1, sis1, sis2, VjLow, VjHigh, VjStep, True)
    return MessageResponse(message = "I-V Curve started", success = True)

@router.get("/ivcurve", response_model = IVCurveResults)
async def get_IVCurve():
    return FEMC.CartAssembly.ivCurveResults