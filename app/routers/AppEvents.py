from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
from .ConnectionManager import ConnectionManager
import logging
from pydantic import BaseModel
from typing import Optional, Union
import app.routers.AppEventsQueue as AppEventsQueue
import queue
import time

logger = logging.getLogger("ALMAFE-CTS-Control")
router = APIRouter(prefix = "/event")
manager = ConnectionManager()

class Event(BaseModel):
    type: str
    iter: Union[int, str] = 0
    x: Optional[float] = None
    y: Optional[float] = None

    def getText(self):
        return f"Event {self.type}: {self.iter}, {self.x}, {self.y}"

def addEvent(item: Event):
    AppEventsQueue.eventQueue.put(item)
    
def getEvent() -> Event:
    try:
        item = AppEventsQueue.eventQueue.get_nowait()
    except queue.Empty:
        item = None
    return item

@router.websocket("/event_ws")
async def websocket_actionPublisher(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(0.1)
            item = getEvent()
            if item:
                # logger.debug(item.getText())
                await manager.send(item.dict(), websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /event_ws")
