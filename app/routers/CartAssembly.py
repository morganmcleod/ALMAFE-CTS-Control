from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import hardware.FEMC as FEMC
from Response import MessageResponse

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
manager = ConnectionManager()

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
async def set_AutoLOPower(pol: int):
    pol0 = True if pol == 0 else False
    pol1 = True if pol == 1 else False

    if not FEMC.cartAssembly.setAutoLOPower(pol0, pol1, onThread = True):
        return MessageResponse(message = f"Auto LO power failed pol={pol}", success = False)
    else:
        return MessageResponse(message = f"Setting auto LO power for pol={pol}...", success = True)
