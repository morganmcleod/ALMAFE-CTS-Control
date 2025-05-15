import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app_Common.Response import MessageResponse
from .LO import router as loRouter
from Controllers.schemas.DeviceInfo import DeviceInfo
from Controllers.IFSystem.Interface import OutputSelect
from app_Common.ConnectionManager import ConnectionManager

import app_MTS2.hardware.RFSource
rfSource = app_MTS2.hardware.RFSource.rfSource
import app_MTS2.hardware.IFSystem
ifSystem = app_MTS2.hardware.IFSystem.ifSystem
import app_MTS2.hardware.PowerDetect
powerDetect = app_MTS2.hardware.PowerDetect.powerDetect

router = APIRouter()
router.include_router(loRouter)
manager = ConnectionManager()
logger = logging.getLogger("ALMAFE-CTS-Control")

@router.get("/device_info", response_model = DeviceInfo)
async def get_DeviceInfo_RFSource():
    return rfSource.getDeviceInfo()

@router.websocket("/auto_rf/power_ws")
async def websocket_rf_power(websocket: WebSocket):
    await manager.connect(websocket)
    last_measured = None
    try:
        while True:
            status = rfSource.getAutoRFStatus()
            if status.is_active and status.last_measured != last_measured:
                last_measured = status.last_measured
                await manager.send(status.last_measured, websocket)            
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocketDisconnect: /power_ws")

@router.put("/auto_rf", response_model = MessageResponse)
async def set_AutoRF(freqIF: float = 10, target: float = -5, atten: int = 22, reinitialize: bool = False):
    ifSystem.output_select = OutputSelect.POWER_DETECT
    ifSystem.attenuation = atten
    ifSystem.frequency = freqIF
    success, msg = rfSource.autoRFPower(powerDetect, target, reinitialize, on_thread = True)
    return MessageResponse(message = "Auto RF power: " + msg, success = success)
    
