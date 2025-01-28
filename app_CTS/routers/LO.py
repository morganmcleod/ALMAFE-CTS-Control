from fastapi import APIRouter, Request, Depends
from Controllers.schemas.LO import *
from app_Common.schemas.common import *
from app_Common.Response import MessageResponse
from Controllers.schemas.DeviceInfo import DeviceInfo
import hardware.FEMC as FEMC

router = APIRouter()

def getTarget(request: Request):
    if "/rfsource" in request.url.path:
        return FEMC.rfSrcDevice, "RF Source"
    else:
        return FEMC.loDevice, "LO"

@router.get("/device_info", response_model = DeviceInfo)
async def get_DeviceInfo_LO(request: Request):
    device, name = getTarget(request)
    return DeviceInfo(
        name = name,
        resource = "CAN0:13",
        connected = device.connected()
    )

@router.put("/yto/limits", response_model = MessageResponse)
async def set_YTO_Limits(request: Request, payload: ConfigYTO):
    device, name = getTarget(request)
    device.setYTOLimits(payload.lowGHz, payload.highGHz)
    return MessageResponse(message = f"{name} YTO: " + payload.getText(), success = True)

@router.put("/yto/coursetune", response_model = MessageResponse)
async def set_YTO_CourseTune(request: Request, value: int):
    device, name = getTarget(request)
    result = device.setYTOCourseTune(value)
    if result:
        return MessageResponse(message = f"{name} set YTO course tune {value}", success = True)
    else:
        return MessageResponse(message = f"{name} YTO set course tune FAILED", success = False)

@router.put("/frequency", response_model = MessageResponse)
async def set_Frequency(request: Request, freqGHz: float):
    device, name = getTarget(request)
    (wcaFreq, ytoFreq, ytoCourse) = device.setFrequency(freqGHz)
    if wcaFreq:
        wcaText = f" [wcaFreq:{wcaFreq} ytoFreq:{ytoFreq} ytoCourse:{ytoCourse}]"
        return MessageResponse(message = f"{name} set frequency {freqGHz} GHz" + wcaText, success = True)
    else:
        return MessageResponse(message = f"{name} set frequency {freqGHz} GHz FAILED", success = False)

@router.put("/pll/lock", response_model = MessageResponse)
async def lock_PLL(request: Request, payload: LOSettings):
    device, name = getTarget(request)
    (wcaFreq, ytoFreq, ytoCourse) = device.lockPLL(payload.freqLOGHz)
    if wcaFreq:
        if name == "LO":
            FEMC.cartAssembly.setBias(payload.freqLOGHz)
        wcaText = f" [wcaFreq:{wcaFreq} ytoFreq:{ytoFreq} ytoCourse:{ytoCourse}]"
        return MessageResponse(message = f"{name} PLL LOCKED " + payload.getText() + wcaText, success = True)
    else:
        return MessageResponse(message = f"{name} PLL lock FAILED " + payload.getText(), success = False)

@router.put("/pll/adjust", response_model = MessageResponse)
async def adjust_PLL(request: Request, payload: AdjustPLL):
    device, name = getTarget(request)
    CV = device.adjustPLL(payload.targetCV)
    if CV is not None:
        return MessageResponse(message = f"{name} PLL adjusted CV:{CV} device: {payload.getText()}", success = True)
    else:
        return MessageResponse(message = f"{name} PLL adjust FAILED: device: {payload.getText()}", success = False)

@router.put("/pll/clearunlock", response_model = MessageResponse)
async def clear_Unlock_Detect(request: Request):
    device, name = getTarget(request)
    device.clearUnlockDetect()
    return MessageResponse(message = f"{name} PLL cleared unlock detect.", success = True)

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
    assert(device)
    if payload.loopBW is not None:
        device.selectLoopBW(payload.loopBW)
    if payload.lockSB is not None:
        device.selectLockSideband(payload.lockSB)
    return MessageResponse(message = f"{name} PLL config " + payload.getText(), success = True)
    
@router.put("/pll/nullintegrator", response_model = MessageResponse)
async def setNullLoopIntegrator(request: Request, payload:SingleBool):
    device, name = getTarget(request)
    device.setNullLoopIntegrator(payload.value)
    return MessageResponse(message = f"{name} PLL null integrator " + payload.getText(), success = True)

@router.put("/photomixer/enable", response_model = MessageResponse)
async def set_Photmixer_Enable(request: Request, payload:SingleBool):
    device, name = getTarget(request)
    device.enablePhotomixer(payload.value)
    return MessageResponse(message = f"{name} Photomixer " + payload.getText(), success = True)

@router.put("/pa/bias", response_model = MessageResponse)
async def set_PA_Bias(request: Request, payload: SetPA):
    device, name = getTarget(request)
    result = device.setPABias(payload.pol, payload.VDControl, payload.VG)
    if result:
        return MessageResponse(message = f"{name} PA bias " + payload.getText(), success = True)
    else:
        return MessageResponse(message = f"{name} PA bias FAILED " + payload.getText(), success = False)
    
@router.put("/pa/teledyne", response_model = MessageResponse)
async def set_Teledyne_PA_Config(request: Request, payload: TeledynePA):
    device, name = getTarget(request)
    result = device.setTeledynePAConfig(payload.hasTeledyne, payload.collectorP0, payload.collectorP1)
    if result:
        return MessageResponse(message = f"{name} Teledyne PA config " + payload.getText(), success = True)
    else:
        return MessageResponse(message = f"{name} Teledyne PA config FAILED " + payload.getText(), success = False)

@router.get("/yto", response_model = YTO)
async def get_YTO(request: Request):
    device, name = getTarget(request)
    data = device.getYTO()
    return YTO.parse_obj(data)
    
@router.get("/pll", response_model = PLL)
async def get_PLL(request: Request):
    device, name = getTarget(request)
    data = device.getPLL()
    return PLL.parse_obj(data)

@router.get("/pll/lock", response_model = LockInfo)
async def get_PLL_lockinfo(request: Request):
    device, name = getTarget(request)
    data = device.getLockInfo()
    return LockInfo.parse_obj(data)

@router.get("/pll/config", response_model = PLLConfig)
async def get_PLL_Config(request: Request):
    device, name = getTarget(request)
    data = device.getPLLConfig()
    return PLLConfig.parse_obj(data)

@router.get("/photomixer", response_model = Photomixer)
async def get_Photomixer(request: Request):
    device, name = getTarget(request)
    data = device.getPhotomixer()
    return Photomixer.parse_obj(data)

@router.get("/amc", response_model = AMC)
async def get_AMC(request: Request):
    device, name = getTarget(request)
    data = device.getAMC()
    return AMC.parse_obj(data)

@router.get("/pa", response_model = PA)
async def get_PA(request: Request):
    device, name = getTarget(request)
    data = device.getPA()
    return PA.parse_obj(data)

@router.get("/teledynepa", response_model = TeledynePA)
async def get_Teledyne_PA(request: Request):
    device, name = getTarget(request)
    data = device.getTeledynePA()
    return TeledynePA.parse_obj(data)
