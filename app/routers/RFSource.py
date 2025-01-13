import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.schemas.Response import MessageResponse
from Control.schemas.DeviceInfo import DeviceInfo
from .LO import router as loRouter
import hardware.FEMC
rfSrcDevice = hardware.FEMC.rfSrcDevice
import hardware.IFSystem
ifSystem = hardware.IFSystem.ifSystem
import hardware.PowerDetect
powerDetect = hardware.PowerDetect.powerDetect
import hardware.BeamScanner
pna = hardware.BeamScanner.pna
from Control.IFSystem.Interface import OutputSelect
from Control.PowerDetect.PDPNA import PDPNA
from Control.RFAutoLevel import RFAutoLevel
from .ConnectionManager import ConnectionManager
from INSTR.PNA.AgilentPNA import FAST_CONFIG, DEFAULT_POWER_CONFIG

router = APIRouter()
router.include_router(loRouter)
manager = ConnectionManager()
logger = logging.getLogger("ALMAFE-CTS-Control")

rfAutoLevel = RFAutoLevel(
    ifSystem, 
    powerDetect,
    rfSrcDevice
)

@router.websocket("/auto_rf/power_ws")
async def websocket_rf_power(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        lastValue = None
        while True:
            if rfAutoLevel.last_read != lastValue:
                lastValue = rfAutoLevel.last_read
                await manager.send(lastValue, websocket)            
            await asyncio.sleep(0.01)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /power_ws")

@router.put("/auto_rf/meter", response_model = MessageResponse)
async def set_AutoRFMeter(freqIF: float = 10, target: float = -5, atten: int = 22):
    ifSystem.output_select = OutputSelect.POWER_DETECT
    ifSystem.attenuation = atten
    success, msg = rfAutoLevel.autoLevel(freqIF, target)
    return MessageResponse(message = "Auto RF power with meter: " + msg, success = success)
    
@router.put("/auto_rf/pna", response_model = MessageResponse)
async def set_AutoRFPNA(freqIF: float = 10, target: float = -5, atten: int = 22):
    ifSystem.output_select = OutputSelect.PNA_INTERFACE
    ifSystem.attenuation = atten
    powerDetectPNA = PDPNA(pna)
    powerDetectPNA.configure(config = FAST_CONFIG, power_config = DEFAULT_POWER_CONFIG)
    success, msg = rfAutoLevel.autoLevel(freqIF, target, powerDetect = powerDetectPNA)
    return MessageResponse(message = "Auto RF power with PNA: " + msg, success = success)
