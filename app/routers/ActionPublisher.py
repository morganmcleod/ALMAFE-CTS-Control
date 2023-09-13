from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
from .ConnectionManager import ConnectionManager
import logging
logger = logging.getLogger("ALMAFE-CTS-Control")
import app.routers.ActionQueue as ActionQueue

async def __addPlotPoint(item):
    await ActionQueue.actionQueue.put(item)
    await asyncio.sleep(0.1)

def addPlotPoint(item):
    try:
        loop = addPlotPoint.loop
    except:
        try:
            loop = addPlotPoint.loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
    if loop and loop.is_running():
        loop.create_task(__addPlotPoint(item))
    else:
        asyncio.run(__addPlotPoint(item))

router = APIRouter(prefix="/action")
manager = ConnectionManager()

@router.websocket("/action_ws")
async def websocket_actionPublisher(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            try:
                item = ActionQueue.actionQueue.get_nowait()
            except asyncio.QueueEmpty:
                item = None
            if item:
                await manager.send(item.dict(), websocket)
            else:
                await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /action_ws")
