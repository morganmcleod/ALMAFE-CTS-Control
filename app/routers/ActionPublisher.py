from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
from .ConnectionManager import ConnectionManager
import logging
logger = logging.getLogger("ALMAFE-CTS-Control")
import app.routers.ActionQueue as ActionQueue

async def asyncAddItem(item):
    await ActionQueue.actionQueue.put(item)
    await asyncio.sleep(0.01)
    
def addItem(item):
    try:
        loop = addItem.loop
    except:
        try:
            loop = addItem.loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
    if loop and loop.is_running():
        loop.create_task(asyncAddItem(item))
    else:
        asyncio.run(asyncAddItem(item))

router = APIRouter(prefix = "/app")
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
                try:
                    item = item.dict()
                except:
                    pass
                await manager.send(item, websocket)
            else:
                await asyncio.sleep(0.01)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /action_ws")
