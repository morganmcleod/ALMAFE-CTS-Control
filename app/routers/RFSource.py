import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.schemas.Response import MessageResponse
from Control.schemas.DeviceInfo import DeviceInfo
from .LO import router as loRouter
from hardware.FEMC import rfSrcDevice
from hardware.IFSystem import ifSystem
from hardware.PowerDetect import powerDetect
from hardware.BeamScanner import pna
from Control.IFSystem.Interface import OutputSelect
from Control.PowerDetect.PDPNA import PDPNA
from Control.RFAutoLevel import RFAutoLevel
from .ConnectionManager import ConnectionManager

router = APIRouter()
router.include_router(loRouter)
manager = ConnectionManager()
logger = logging.getLogger("ALMAFE-CTS-Control")

@router.get("/device_info", response_model = DeviceInfo)
async def get_DeviceInfo_RFSource():
    return DeviceInfo(
        name = 'RF Source',
        resource = "CAN0:13",
        connected = rfSrcDevice.connected()
    )

@router.websocket("/auto_rf/power_ws")
async def websocket_rf_power(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        lastValue = None
        while True:
            if rfSrcDevice.autoRfPowerValue is None:
                lastValue = None
            elif rfSrcDevice.autoRfPowerValue != lastValue:
                lastValue = rfSrcDevice.autoRfPowerValue
                await manager.send(rfSrcDevice.autoRfPowerValue, websocket)            
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /auto_rf/power_ws")

@router.put("/auto_rf/meter", response_model = MessageResponse)
async def set_AutoRFMeter(freqIF: float = 10, target: float = -5, atten: int = 22):
    ifSystem.output_select = OutputSelect.PNA_INTERFACE
    ifSystem.attenuation = atten
    autoLevel = RFAutoLevel(ifSystem, powerDetect, rfSrcDevice)
    success, msg = autoLevel.autoLevel(freqIF, target)
    return MessageResponse(message = "Auto RF power with meter: " + msg, success = success)
    
@router.put("/auto_rf/pna", response_model = MessageResponse)
async def set_AutoRFPNA(freqIF: float = 10, target: float = -5, atten: int = 22):
    ifSystem.output_select = OutputSelect.POWER_DETECT
    ifSystem.attenuation = atten
    powerDetectPNA = PDPNA(pna)
    autoLevel = RFAutoLevel(ifSystem, powerDetectPNA, rfSrcDevice)
    success, msg = autoLevel.autoLevel(freqIF, target)
    return MessageResponse(message = "Auto RF power with PNA: " + msg, success = success)
