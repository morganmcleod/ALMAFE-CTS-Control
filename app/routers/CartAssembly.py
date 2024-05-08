from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import hardware.FEMC as FEMC
from app.schemas.Response import MessageResponse
from schemas.DeviceInfo import DeviceInfo
from schemas.common import SingleBool
from .ConnectionManager import ConnectionManager
import asyncio
import logging

logger = logging.getLogger("ALMAFE-CTS-Control")
router = APIRouter(prefix="/cartassy")
manager = ConnectionManager()

@router.websocket("/sis/current_ws")
async def websocket_sis_current(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        prevSis0 = prevSis1 = None
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

@router.get("/device_info", response_model = DeviceInfo)
async def get_DeviceInfo_CartAssembly():
    return DeviceInfo(
        resource_name = "CAN0:13",
        is_connected = FEMC.cartAssembly.isConnected()
    )

@router.put("/auto_lo", response_model = MessageResponse)
async def set_AutoLOPower(pol: int):
    pol0 = True if pol == 0 else False
    pol1 = True if pol == 1 else False

    if not FEMC.cartAssembly.setAutoLOPower(pol0, pol1, onThread = True):
        return MessageResponse(message = f"Auto LO power failed pol={pol}", success = False)
    else:
        return MessageResponse(message = f"Setting auto LO power for pol={pol}...", success = True)
