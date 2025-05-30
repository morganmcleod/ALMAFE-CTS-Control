import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import hardware.FEMC as FEMC
from app_Common.Response import MessageResponse
from app_Common.ConnectionManager import ConnectionManager

logger = logging.getLogger("ALMAFE-CTS-Control")
router = APIRouter(prefix="/cartassy")
manager = ConnectionManager()

@router.websocket("/auto_lo/current_ws")
async def websocket_sis_current(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            status = FEMC.cartAssembly.getAutoLOStatus()
            if status.is_active:
                sis = FEMC.ccaDevice.getSIS(pol = status.polarization, sis=1, averaging=2, nDigits = 1, takeAbs = True)
                await manager.send(sis, websocket)
            await asyncio.sleep(0.01)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocketDisconnect: /cartassy/auto_lo/current_ws")

@router.put("/auto_lo", response_model = MessageResponse)
async def put_AutoLOPower(pol: int):
    pol0 = True if pol in (-1, 0) else False
    pol1 = True if pol in (-1, 1) else False
    success, msg = FEMC.cartAssembly.autoLOPower(pol0 = pol0, pol1 = pol1, on_thread = True)
    if not success:
        return MessageResponse(message = f"Auto LO power failed pol={pol}", success = False)
    else:
        return MessageResponse(message = f"Setting auto LO power for pol={pol}...", success = True)
