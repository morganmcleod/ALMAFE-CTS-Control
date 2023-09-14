from fastapi import APIRouter
import hardware.FEMC as FEMC
from Response import MessageResponse

router = APIRouter(prefix="/cartassy")

@router.put("/auto_lo", response_model = MessageResponse)
async def set_AutoLOPower(pol: int):
    pol0 = True if pol == 0 else False
    pol1 = True if pol == 1 else False

    if not FEMC.cartAssembly.setAutoLOPower(pol0, pol1):
        return MessageResponse(message = f"Auto LO Power failed pol={pol}", success = False)
    else:
        return MessageResponse(message = f"Auto LO Power done pol={pol}", success = True)
