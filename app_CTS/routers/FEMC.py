from fastapi import APIRouter
from app_Common.Response import MessageResponse
from app_Common.schemas.common import SingleInt, SingleFloat
from Controllers.schemas.DeviceInfo import DeviceInfo
import hardware.FEMC as FEMC
from typing import List

router = APIRouter(prefix="/femc")

@router.get("/device_info", response_model = DeviceInfo)
async def get_DeviceInfo_FEMC():
    return DeviceInfo(
        name = 'FEMC module',
        resource = "CAN0:13",
        connected = FEMC.femcDevice.connected()
    )

@router.get("/femcversion", response_model = MessageResponse)
def getFemcVersion() -> str:
    return MessageResponse(message = FEMC.femcDevice.getFemcVersion(), success = True)

@router.get("/ambsiversion", response_model = MessageResponse)
def getFemcVersion() -> str:
    return MessageResponse(message = FEMC.femcDevice.getAmbsiVersion(), success = True)

@router.get("/esnlist", response_model = List[str])
async def getEsnList():
    return [
        f"{esn[0]:02X} {esn[1]:02X} {esn[2]:02X} {esn[3]:02X} {esn[4]:02X} {esn[5]:02X} {esn[6]:02X} {esn[7]:02X}"
        for esn in FEMC.femcDevice.getEsnList()
    ]

@router.get("/numtransactions", response_model = SingleInt)
async def getErrorCount():
    return SingleInt(value = FEMC.femcDevice.getAmbsiNumTrans())

@router.get("/numerrors", response_model = SingleInt)
async def getErrorCount():
    return SingleInt(value = FEMC.femcDevice.getAmbsiErrors())

@router.get("/ambsitemperature", response_model = SingleFloat)
async def getErrorCount():
    return SingleFloat(value = FEMC.femcDevice.getAmbsiTemperature())
