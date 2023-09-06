from fastapi import APIRouter, Request
from Response import MessageResponse
from .LO import router as loRouter
import hardware.FEMC as FEMC
import hardware.NoiseTemperature as NT
import hardware.BeamScanner as BeamScanner

router = APIRouter()
router.include_router(loRouter)
router.hardwareDevice = FEMC.rfSrcDevice

@router.put("/auto_rf/powermeter/{target}", response_model = MessageResponse)
async def set_AutoRFPowerMeter(request: Request, target: float):
    if not router.hardwareDevice.autoRFPowerMeter(NT.powerMeter, target, onThread = True):
        return MessageResponse(message = "Auto RF PowerMeter failed", success = False)
    else:
        return MessageResponse(message = "Auto RF PowerMeter done", success = True)
    
@router.put("/auto_rf/pna/{target}", response_model = MessageResponse)
async def set_AutoRFPNA(request: Request, target: float):
    if not router.hardwareDevice.autoRFPNA(BeamScanner.pna, target, onThread = True):
        return MessageResponse(message = "Auto RF PNA failed", success = False)
    else:
        return MessageResponse(message = "Auto RF PNA done", success = True)
