from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
from .ConnectionManager import ConnectionManager
import logging
from pydantic import BaseModel
from typing import Optional, Union
import app.routers.AppEventsQueue as AppEventsQueue

logger = logging.getLogger("ALMAFE-CTS-Control")
router = APIRouter(prefix = "/event")
manager = ConnectionManager()

class Event(BaseModel):
    type: str
    iter: Union[int, str] = 0
    x: Optional[float] = None
    y: Optional[float] = None

async def asyncAddEvent(item):
    await AppEventsQueue.eventQueue.put(item)
    await asyncio.sleep(0.01)
    
def addEvent(item):
    try:
        loop = addEvent.loop
    except:
        try:
            loop = addEvent.loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
    if loop and loop.is_running():
        loop.create_task(asyncAddEvent(item))
    else:
        asyncio.run(asyncAddEvent(item))

@router.websocket("/event_ws")
async def websocket_actionPublisher(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            try:
                item = AppEventsQueue.eventQueue.get_nowait()
            except asyncio.QueueEmpty:
                item = None
            if item:                
                await manager.send(item.dict(), websocket)
            await asyncio.sleep(0.01)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /action_ws")
