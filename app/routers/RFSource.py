from fastapi import APIRouter, Request, Depends, WebSocket, WebSocketDisconnect
from app.schemas.Response import MessageResponse
from schemas.common import SingleBool
from schemas.DeviceInfo import DeviceInfo
from .LO import router as loRouter
from hardware.FEMC import rfSrcDevice
from hardware.NoiseTemperature import powerMeter
from hardware.BeamScanner import pna
from hardware.WarmIFPlate import warmIFPlate
from CTSDevices.WarmIFPlate.OutputSwitch import PadSelect, LoadSelect, OutputSelect
from .ConnectionManager import ConnectionManager
import asyncio
import logging

router = APIRouter()
router.include_router(loRouter)
manager = ConnectionManager()
logger = logging.getLogger("ALMAFE-CTS-Control")

@router.get("/device_info", response_model = DeviceInfo)
async def get_DeviceInfo_RFSource():
    return DeviceInfo(
        resource_name = "CAN0:13",
        is_connected = rfSrcDevice.isConnected()
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
async def set_AutoRFMeter(request: Request, freqIF: float = 10, target: float = -5, atten: int = 22):
    warmIFPlate.outputSwitch.setValue(OutputSelect.POWER_METER, LoadSelect.THROUGH, PadSelect.PAD_OUT)        
    warmIFPlate.attenuator.setValue(atten)
    warmIFPlate.yigFilter.setFrequency(freqIF)
    if not rfSrcDevice.autoRFPower(powerMeter, target, onThread = True):
        return MessageResponse(message = "Auto RF power with meter failed", success = False)
    else:
        return MessageResponse(message = "Setting auto RF power with meter...", success = True)
    
@router.put("/auto_rf/pna", response_model = MessageResponse)
async def set_AutoRFPNA(request: Request, freqIF: float = 10, target: float = -5, atten: int = 22):
    warmIFPlate.outputSwitch.setValue(OutputSelect.SQUARE_LAW, LoadSelect.THROUGH, PadSelect.PAD_OUT)        
    warmIFPlate.attenuator.setValue(atten)
    warmIFPlate.yigFilter.setFrequency(freqIF)
    if not rfSrcDevice.autoRFPower(pna, target, onThread = True):
        return MessageResponse(message = "Auto RF power with PNA failed", success = False)
    else:
        return MessageResponse(message = "Setting auto RF power with PNA...", success = True)
