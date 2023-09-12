from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
from .ConnectionManager import ConnectionManager
import logging
logger = logging.getLogger("ALMAFE-CTS-Control")
import app.routers.ActionQueue as ActionQueue

def setItem(item):
    ActionQueue.actionQueue.put(item)
    pass

router = APIRouter(prefix="/action")
manager = ConnectionManager()

@router.websocket("/action_ws")
async def websocket_actionPublisher(websocket: WebSocket):
    global actionQueue
    await manager.connect(websocket)
    try:
        while True:
            if not ActionQueue.actionQueue.empty():
                item = ActionQueue.actionQueue.get()
                await manager.send(item.dict(), websocket)
            await asyncio.sleep(0.2)            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /action_ws")
