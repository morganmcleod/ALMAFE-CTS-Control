from fastapi import APIRouter, Request
from schemas.LO import *
from schemas.common import *
from Response import MessageResponse
import hardware.FEMC as FEMC

router = APIRouter()

def getTarget(request: Request):
    if "/rfsource" in request.url.path:
        return (FEMC.rfSrcDevice, "RF Source")
    elif "/lo" in request.url.path:
        return (FEMC.loDevice, "LO")
    else:
        return (None, "")

@router.get("/connected", response_model = SingleBool)
async def get_isConnected(request: Request):
    target, _ = getTarget(request)
    assert(target)
    return SingleBool(value = target.isConnected())

@router.put("/yto/limits", response_model = MessageResponse)
async def set_YTO_Limits(request: Request, payload: ConfigYTO):
    target, name = getTarget(request)
    assert(target)
    target.setYTOLimits(payload.lowGHz, payload.highGHz)
    return MessageResponse(message = f"{name} YTO: " + payload.getText(), success = True)

@router.put("/yto/coursetune", response_model = MessageResponse)
async def set_YTO_CourseTune(request: Request, payload: SetYTO):
    target, name = getTarget(request)
    assert(target)
    result = target.setYTOCourseTune(payload.courseTune)
    if result:
        return MessageResponse(message = f"{name} YTO courseTune " + payload.getText(), success = True)
    else:
        return MessageResponse(message = f"{name} YTO courseTune FAILED: " + payload.getText(), success = False)

@router.put("/frequency", response_model = MessageResponse)
async def set_Frequency(request: Request, payload: SetLOFrequency):
    target, name = getTarget(request)
    assert(target)
    (wcaFreq, ytoFreq, ytoCourse) = target.setLOFrequency(payload.freqGHz)
    if wcaFreq:
        wcaText = f" [wcaFreq:{wcaFreq} ytoFreq:{ytoFreq} ytoCourse:{ytoCourse}]"
        return MessageResponse(message = f"{name} frequency " + payload.getText() + wcaText, success = True)
    else:
        return MessageResponse(message = f"{name} frequency FAILED: " + payload.getText(), success = False)

@router.put("/pll/lock", response_model = MessageResponse)
async def lock_PLL(request: Request, payload: LockPLL):
    target, name = getTarget(request)
    assert(target)
    (wcaFreq, ytoFreq, ytoCourse) = target.lockPLL(payload.freqLOGHz, payload.freqFloogGHz)
    if wcaFreq:
        wcaText = f" [wcaFreq:{wcaFreq} ytoFreq:{ytoFreq} ytoCourse:{ytoCourse}]"
        return MessageResponse(message = f"{name} PLL LOCKED " + payload.getText() + wcaText, success = True)
    else:
        return MessageResponse(message = f"{name} PLL lock FAILED " + payload.getText(), success = False)

@router.put("/pll/adjust", response_model = MessageResponse)
async def adjust_PLL(request: Request, payload: AdjustPLL):
    target, name = getTarget(request)
    assert(target)
    CV = target.adjustPLL(payload.targetCV)
    if CV is not None:
        return MessageResponse(message = f"{name} PLL adjusted CV:{CV} target: {payload.getText()}", success = True)
    else:
        return MessageResponse(message = f"{name} PLL adjust FAILED: target: {payload.getText()}", success = False)

@router.put("/pll/clearunlock", response_model = MessageResponse)
async def clear_Unlock_Detect(request: Request):
    target, name = getTarget(request)
    assert(target)
    target.clearUnlockDetect()
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
    target, name = getTarget(request)
    assert(target)
    if payload.loopBW is not None:
        target.selectLoopBW(payload.loopBW)
    if payload.lockSB is not None:
        target.selectLockSideband(payload.lockSB)
    return MessageResponse(message = f"{name} PLL config " + payload.getText(), success = True)
    
@router.put("/pll/nullintegrator", response_model = MessageResponse)
async def setNullLoopIntegrator(request: Request, payload:SingleBool):
    target, name = getTarget(request)
    assert(target)
    target.setNullLoopIntegrator(payload.value)
    return MessageResponse(message = f"{name} PLL null integrator " + payload.getText(), success = True)

@router.put("/photomixer/enable", response_model = MessageResponse)
async def set_Photmixer_Enable(request: Request, payload:SingleBool):
    target, name = getTarget(request)
    assert(target)
    target.setPhotmixerEnable(payload.value)
    return MessageResponse(message = f"{name} Photomixer " + payload.getText(), success = True)

@router.put("/pa/bias", response_model = MessageResponse)
async def set_PA_Bias(request: Request, payload: SetPA):
    target, name = getTarget(request)
    assert(target)
    result = target.setPABias(payload.pol, payload.VDControl, payload.VG)
    if result:
        return MessageResponse(message = f"{name} PA bias " + payload.getText(), success = True)
    else:
        return MessageResponse(message = f"{name} PA bias FAILED " + payload.getText(), success = False)
    
@router.put("/pa/teledyne", response_model = MessageResponse)
def set_Teledyne_PA_Config(request: Request, payload: TeledynePA):
    target, name = getTarget(request)
    assert(target)
    result = target.setTeledynePAConfig(payload.hasTeledyne, payload.collectorP0, payload.collectorP1)
    if result:
        return MessageResponse(message = f"{name} Teledyne PA config " + payload.getText(), success = True)
    else:
        return MessageResponse(message = f"{name} Teledyne PA config FAILED " + payload.getText(), success = False)

@router.get("/yto", response_model = YTO)
async def get_YTO(request: Request):
    target, _ = getTarget(request)
    assert(target)
    data = target.getYTO()
    return YTO.parse_obj(data)
    
@router.get("/pll", response_model = PLL)
async def get_PLL(request: Request):
    target, _ = getTarget(request)
    assert(target)
    data = target.getPLL()
    return PLL.parse_obj(data)

@router.get("/pll/config", response_model = PLLConfig)
async def get_PLL_Config(request: Request):
    target, _ = getTarget(request)
    assert(target)
    data = target.getPLLConfig()
    return PLLConfig.parse_obj(data)

@router.get("/photomixer", response_model = Photomixer)
async def get_Photomixer(request: Request):
    target, _ = getTarget(request)
    assert(target)
    data = target.getPhotomixer()
    return Photomixer.parse_obj(data)

@router.get("/amc", response_model = AMC)
async def get_AMC(request: Request):
    target, _ = getTarget(request)
    assert(target)
    data = target.getAMC()
    return AMC.parse_obj(data)

@router.get("/pa", response_model = PA)
async def get_PA(request: Request):
    target, _ = getTarget(request)
    assert(target)
    data = target.getPA()
    return PA.parse_obj(data)

@router.get("/teledynepa", response_model = TeledynePA)
async def get_Teledyne_PA(request: Request):
    target, _ = getTarget(request)
    assert(target)
    data = target.getTeledynePA()
    return TeledynePA.parse_obj(data)
