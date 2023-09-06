from fastapi import APIRouter
import hardware.FEMC as FEMC
from Response import MessageResponse

router = APIRouter(prefix="/cartassy")

@router.put("/auto_lo", response_model = MessageResponse)
async def set_AutoLOPower():
    if not FEMC.cartAssembly.setAutoLOPower(pol = 0, onThread = True):
        return MessageResponse(message = "Auto LO Power failed for pol0", success = False)
    elif not FEMC.cartAssembly.setAutoLOPower(pol = 1, onThread = True):
        return MessageResponse(message = "Auto LO Power failed for pol1", success = False)
    else:
        return MessageResponse(message = "Auto LO Power done", success = True)
