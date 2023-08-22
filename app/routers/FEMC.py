from fastapi import APIRouter
from Response import MessageResponse
from schemas.common import SingleInt, SingleFloat
import hardware.FEMC as FEMC

router = APIRouter(prefix="/femc")

@router.get("/femcversion", response_model = MessageResponse)
def getFemcVersion() -> str:
    return MessageResponse(message = FEMC.femcDevice.getFemcVersion(), success = True)

@router.get("/ambsiversion", response_model = MessageResponse)
def getFemcVersion() -> str:
    return MessageResponse(message = FEMC.femcDevice.getAmbsiSoftwareRev(), success = True)

@router.get("/esnstring", response_model = MessageResponse)
async def getEsnString():
    return MessageResponse(message = FEMC.femcDevice.getEsnString(), success = True)

@router.get("/numtransactions", response_model = SingleInt)
async def getErrorCount():
    return SingleInt(value = FEMC.femcDevice.getAmbsiNumTrans())

@router.get("/numerrors", response_model = SingleInt)
async def getErrorCount():
    return SingleInt(value = FEMC.femcDevice.getAmbsiErrors())

@router.get("/ambsitemperature", response_model = SingleFloat)
async def getErrorCount():
    return SingleFloat(value = FEMC.femcDevice.getAmbsiTemperature())
