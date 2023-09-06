from fastapi import APIRouter, Request
from Response import MessageResponse
from .LO import router as loRouter
import hardware.FEMC as FEMC
import hardware.NoiseTemperature as NT
import hardware.BeamScanner as BeamScanner
import hardware.WarmIFPlate as WarmIFPlate

router = APIRouter()
router.include_router(loRouter)
router.hardwareDevice = FEMC.rfSrcDevice
router.name = "RF Source"

@router.put("/auto_rf/meter", response_model = MessageResponse)
async def set_AutoRFMeter(request: Request, freqIF: float, target: float):
    if not router.hardwareDevice.autoRFPowerMeter(
            NT.powerMeter,
            WarmIFPlate.warmIFPlate.yigFilter,
            freqIF,
            target,
            onThread = True):
        return MessageResponse(message = "Auto RF Power Meter failed", success = False)
    else:
        return MessageResponse(message = "Auto RF Power Meter done", success = True)
    
@router.put("/auto_rf/pna", response_model = MessageResponse)
async def set_AutoRFPNA(request: Request, freqIF: float, target: float):
    if not router.hardwareDevice.autoRFPNA(
            BeamScanner.pna,            
            WarmIFPlate.warmIFPlate.yigFilter,
            freqIF,
            target,
            onThread = True):
        return MessageResponse(message = "Auto RF PNA failed", success = False)
    else:
        return MessageResponse(message = "Auto RF PNA done", success = True)
