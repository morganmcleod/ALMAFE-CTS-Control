from fastapi import WebSocket
from websockets.exceptions import ConnectionClosed
from typing import List, Any
import logging
class ConnectionManager():
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.logger = logging.getLogger("ALMAFE-CTS-Control")

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send(self, message: Any, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except ConnectionClosed:
            pass
        except Exception as e:
            self.logger.exception("ConnectionManager.send", e)

    async def broadcast(self, message: Any):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                self.logger.exception("ConnectionManager.broadcast", e)
