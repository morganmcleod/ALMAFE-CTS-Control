from fastapi import APIRouter, Request
from hardware.ReferenceSources import loReference, rfReference
from schemas.common import SingleBool
from schemas.ReferenceSource import ReferenceSourceStatus
from Response import MessageResponse

router = APIRouter()

def getTarget(request: Request):
    if "/rfref" in request.url.path:
        return (rfReference, "LO Ref")
    elif "/loref" in request.url.path:
        return (loReference, "RF Ref")
    else:
        return (None, "")

@router.get("/connected", response_model = SingleBool)
async def get_isConnected(request: Request):
    target, _ = getTarget(request)
    assert(target)
    return SingleBool(value = target.isConnected())

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
