from fastapi import APIRouter
import hardware.FEMC as FEMC
from Response import MessageResponse

router = APIRouter(prefix="/cartassy")

@router.put("/auto_lo", response_model = MessageResponse)
async def set_AutoLOPower():
    if not FEMC.cartAssembly.setAutoLOPower(onThread = False):
        return MessageResponse(message = "Auto LO Power failed", success = False)
    else:
        return MessageResponse(message = "Auto LO Power done", success = True)
