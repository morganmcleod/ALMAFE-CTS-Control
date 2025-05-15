from fastapi import APIRouter, Request, Depends
from app_Common.schemas.common import *
from Controllers.schemas.LO import *
from app_Common.Response import MessageResponse
from Controllers.schemas.DeviceInfo import DeviceInfo
import app_MTS2.hardware.MixerAssembly
import app_MTS2.hardware.RFSource
loControl = app_MTS2.hardware.MixerAssembly.loControl
rfSource = app_MTS2.hardware.RFSource.rfSource
mixerAssembly = app_MTS2.hardware.MixerAssembly.mixerAssembly

router = APIRouter()

def getTarget(request: Request):
    if "/rfsource" in request.url.path:
        return rfSource, "RF Source"
    else:
        return loControl, "LO"

@router.get("/device_info", response_model = DeviceInfo)
async def get_DeviceInfo_LO(request: Request):
    device, name = getTarget(request)
    return device.getDeviceInfo()

@router.put("/yto/limits", response_model = MessageResponse)
async def set_YTO_Limits(request: Request, payload: ConfigYTO):
    device, name = getTarget(request)
    device.loDevice.setYTOLimits(payload.lowGHz, payload.highGHz)
    return MessageResponse(message = f"{name} YTO: " + payload.getText(), success = True)

@router.put("/yto/coursetune", response_model = MessageResponse)
async def set_YTO_CourseTune(request: Request, value: int):
    device, name = getTarget(request)
    success = device.loDevice.setYTOCourseTune(value)
    if success:
        return MessageResponse(message = f"{name} set YTO course tune {value}", success = True)
    else:
        return MessageResponse(message = f"{name} set YTO course tune FAILED", success = False)

@router.put("/pll/lock", response_model = MessageResponse)
async def lock_PLL(request: Request, freqGHz: float, settings: LOSettings):
    device, name = getTarget(request)
    success, msg = device.setFrequency(freqGHz, settings)
    if success:
        mixerAssembly.setBias(freqGHz)
        if not msg:
            msg = f"{name} PLL LOCKED at {freqGHz} GHz"
        else:
            msg = f"{name} {msg}"
        return MessageResponse(message = msg, success = True)
    else:
        return MessageResponse(message = f"{name} PLL lock FAILED at {freqGHz} GHz: {msg}", success = False)

@router.put("/pll/adjust", response_model = MessageResponse)
async def adjust_PLL(request: Request, payload: AdjustPLL):
    device, name = getTarget(request)
    CV = device.loDevice.adjustPLL(payload.targetCV)
    if CV is not None:
        return MessageResponse(message = f"{name} PLL adjusted CV:{CV} {payload.getText()}", success = True)
    else:
        return MessageResponse(message = f"{name} PLL adjust FAILED: {payload.getText()}", success = False)

@router.put("/pll/clearunlock", response_model = MessageResponse)
async def clear_Unlock_Detect(request: Request):
    device, name = getTarget(request)
    device.loDevice.clearUnlockDetect()
    return MessageResponse(message = "{name} PLL cleared unlock detect.", success = True)

@router.put("/pll/config", response_model = MessageResponse)
async def set_PLL_Config(request: Request, payload: PLLConfig):
    '''
    payload.loopBW is one of:
    -1: Use the band's default loop bandwidth.
     0: Override to use the "normal" loop BW:   7.5MHz/V (Band 2,4,8,9).
     1: Override to use the "alternate" loop BW: 15MHz/V (Band 3,5,6,7,10, and NRAO band 2 prototype).
     None/null: no change 
    payload.lockSB is one of:
     0: Lock BELOW the reference input.
     1: Lock ABOVE the reference input. 
     None/null: no change 
    '''
    device, name = getTarget(request)
    if payload.loopBW is not None:
        device.loDevice.selectLoopBW(payload.loopBW)
    if payload.lockSB is not None:
        device.loDevice.selectLockSideband(payload.lockSB)
    return MessageResponse(message = "{name} PLL config " + payload.getText(), success = True)
    
@router.put("/pll/nullintegrator", response_model = MessageResponse)
async def setNullLoopIntegrator(request: Request, payload: SingleBool):
    device, name = getTarget(request)
    device.loDevice.setNullLoopIntegrator(payload.value)
    return MessageResponse(message = "{name} PLL null integrator " + payload.getText(), success = True)

@router.put("/photomixer/enable", response_model = MessageResponse)
async def set_Photmixer_Enable(request: Request, payload: SingleBool):
    device, name = getTarget(request)
    device.loDevice.enablePhotomixer(payload.value)
    return MessageResponse(message = "{name} Photomixer " + payload.getText(), success = True)

@router.put("/pa/bias", response_model = MessageResponse)
async def set_PA_Bias(request: Request, payload: SetPA):
    device, name = getTarget(request)
    result = device.loDevice.setPABias(payload.pol, payload.VDControl, payload.VG)
    if result:
        return MessageResponse(message = "{name} PA bias " + payload.getText(), success = True)
    else:
        return MessageResponse(message = "{name} PA bias FAILED " + payload.getText(), success = False)
    
@router.put("/pa/teledyne", response_model = MessageResponse)
async def set_Teledyne_PA_Config(request: Request, payload: TeledynePA):
    device, name = getTarget(request)
    result = device.loDevice.setTeledynePAConfig(payload.hasTeledyne, payload.collectorP0, payload.collectorP1)
    if result:
        return MessageResponse(message = "{name} Teledyne PA config " + payload.getText(), success = True)
    else:
        return MessageResponse(message = "{name} Teledyne PA config FAILED " + payload.getText(), success = False)

@router.get("/yto", response_model = YTO)
async def get_YTO(request: Request):
    device, name = getTarget(request)
    try:
        return YTO.model_validate(device.loDevice.getYTO())
    except:
        return None
        
@router.get("/pll", response_model = PLL)
async def get_PLL(request: Request):
    device, name = getTarget(request)
    if device == loControl:
        try:        
            return PLL.model_validate(device.loDevice.getPLL())
        except:
            return None
    elif device == rfSource:
        try:        
            return PLL.model_validate(device.getPLL())
        except:
            return None
        
@router.get("/pll/config", response_model = PLLConfig)
async def get_PLL_Config(request: Request):
    device, name = getTarget(request)
    try:
        return PLLConfig.model_validate(device.loDevice.getPLLConfig())
    except:
        return None

@router.get("/photomixer", response_model = Photomixer)
async def get_Photomixer(request: Request):
    device, name = getTarget(request)
    try:
        return Photomixer.model_validate(device.loDevice.getPhotomixer())
    except:
        return None

@router.get("/amc", response_model = AMC)
async def get_AMC(request: Request):
    device, name = getTarget(request)
    try:        
        return AMC.model_validate(device.loDevice.getAMC())
    except:
        return None

@router.get("/pa", response_model = PA)
async def get_PA(request: Request):
    device, name = getTarget(request)
    try:        
        return PA.model_validate(device.loDevice.getPA())
    except:
        return None
