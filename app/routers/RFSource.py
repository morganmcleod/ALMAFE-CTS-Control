from fastapi import APIRouter, Request, Depends
from Response import MessageResponse
from .LO import router as loRouter, getTarget
import hardware.FEMC as FEMC
import hardware.NoiseTemperature as NT
import hardware.BeamScanner as BeamScanner
import hardware.WarmIFPlate as WarmIFPlate

async def getRFInfo():
    return {"device": FEMC.rfSrcDevice, "name": "RF Source"}

router = APIRouter()
router.include_router(loRouter)

@router.put("/auto_rf/meter", response_model = MessageResponse)
async def set_AutoRFMeter(request: Request, freqIF: float, target: float):
    device, name = getTarget(request)
    if not device.autoRFPowerMeter(
            NT.powerMeter,
            WarmIFPlate.warmIFPlate,
            freqIF,
            target,
            onThread = True):
        return MessageResponse(message = "Auto RF Power Meter failed", success = False)
    else:
        return MessageResponse(message = "Auto RF Power Meter done", success = True)
    
@router.put("/auto_rf/pna", response_model = MessageResponse)
async def set_AutoRFPNA(request: Request, freqIF: float, target: float):
    device, name = getTarget(request)
    if not device.autoRFPNA(
            BeamScanner.pna,            
            WarmIFPlate.warmIFPlate,
            freqIF,
            target,
            onThread = True):
        return MessageResponse(message = "Auto RF PNA failed", success = False)
    else:
        return MessageResponse(message = "Auto RF PNA done", success = True)
