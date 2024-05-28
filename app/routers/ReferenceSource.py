from fastapi import APIRouter, Request
from hardware.ReferenceSources import loReference, rfReference
from schemas.common import SingleBool
from schemas.ReferenceSource import ReferenceSourceStatus
from schemas.DeviceInfo import DeviceInfo
from app.schemas.Response import MessageResponse
from DebugOptions import *

router = APIRouter()

def getTarget(request: Request):
    if "/rfref" in request.url.path:
        return (rfReference, "RF Ref")
    elif "/loref" in request.url.path:
        return (loReference, "LO Ref")
    else:
        return (None, "")

def getTargetShortName(request: Request):
    if "/rfref" in request.url.path:
        return 'rfref'
    elif "/loref" in request.url.path:
        return 'loref'
    else:
        return 'none'

@router.get("/device_info", response_model = DeviceInfo)
async def get_isConnected(request: Request):
    target, name = getTarget(request)
    assert(target)
    if SIMULATE:
        resource_name = f"simulated {name}"
    else:
        resource_name = target.inst.resource_name
    return DeviceInfo(
        name = getTargetShortName(request),
        resource_name = resource_name,
        is_connected = target.isConnected()
    )

@router.get("/status", response_model = ReferenceSourceStatus)
async def get_Status(request: Request):
    target, _ = getTarget(request)
    assert(target)
    return ReferenceSourceStatus(
        freqGHz = target.getFrequency(),
        ampDBm = target.getAmplitude(),
        enable = target.getRFOutput()
    )

@router.put("/frequency", response_model = MessageResponse)
async def put_RefFreq(request: Request, value:float):
    target, name = getTarget(request)
    if target:
        target.setFrequency(value)
        return MessageResponse(message = f"Set {name} freq to {value} GHz", success = True)
    else:
        return MessageResponse(message = f"put_RefFreq: bad URL", success = False)

@router.put("/amplitude", response_model = MessageResponse)
async def put_RefAmpl(request: Request, value:float):
    target, name = getTarget(request)
    if target:
        target.setAmplitude(value)
        return MessageResponse(message = f"Set {name} ampl to {value} dB", success = True)
    else:
        return MessageResponse(message = f"put_RefAmpl: bad URL", success = False)

@router.put("/output", response_model = MessageResponse)
async def put_RefRFOut(request: Request, enable:bool):
    target, name = getTarget(request)
    if target:
        target.setRFOutput(enable)
        return MessageResponse(message = f"{name} output {'enabled' if enable else 'disabled'}", success = True)
    else:
        return MessageResponse(message = f"put_RefRFOut: bad URL", success = False)
