from fastapi import APIRouter, Request
from schemas.LO import *
from schemas.common import *
from Response import MessageResponse
import hardware.FEMC as FEMC

router = APIRouter()

def getTarget(request: Request):
    if "/rfsource" in request.url.path:
        return FEMC.rfSrcDevice
    else:
        return FEMC.loDevice

@router.put("/yto/limits", response_model = MessageResponse)
async def set_YTO_Limits(request: Request, payload: ConfigYTO):
    getTarget(request).setYTOLimits(payload.lowGHz, payload.highGHz)
    return MessageResponse(message = "YTO: " + payload.getText(), success = True)

@router.put("/yto/coursetune", response_model = MessageResponse)
async def set_YTO_CourseTune(request: Request, payload: SetYTO):
    result = getTarget(request).setYTOCourseTune(payload.courseTune)
    if result:
        return MessageResponse(message = "YTO courseTune " + payload.getText(), success = True)
    else:
        return MessageResponse(message = "YTO courseTune FAILED: " + payload.getText(), success = False)

@router.put("/frequency", response_model = MessageResponse)
async def set_LO_Frequency(request: Request, payload: SetLOFrequency):
    (wcaFreq, ytoFreq, ytoCourse) = getTarget(request).setLOFrequency(payload.freqGHz)
    if wcaFreq:
        wcaText = f" [wcaFreq:{wcaFreq} ytoFreq:{ytoFreq} ytoCourse:{ytoCourse}]"
        return MessageResponse(message = "LO frequency " + payload.getText() + wcaText, success = True)
    else:
        return MessageResponse(message = "LO frequency FAILED: " + payload.getText(), success = False)

@router.put("/pll/lock", response_model = MessageResponse)
async def lock_PLL(request: Request, payload: LockPLL):
    (wcaFreq, ytoFreq, ytoCourse) = getTarget(request).lockPLL(payload.freqLOGHz, payload.freqFloogGHz)
    if wcaFreq:
        wcaText = f" [wcaFreq:{wcaFreq} ytoFreq:{ytoFreq} ytoCourse:{ytoCourse}]"
        return MessageResponse(message = "PLL LOCKED " + payload.getText() + wcaText, success = True)
    else:
        return MessageResponse(message = "PLL lock FAILED " + payload.getText(), success = False)

@router.put("/pll/adjust", response_model = MessageResponse)
async def adjust_PLL(request: Request, payload: AdjustPLL):
    CV = getTarget(request).adjustPLL(payload.targetCV)
    if CV is not None:
        return MessageResponse(message = f"PLL adjusted CV:{CV} [target:" + payload.getText + "]", success = True)
    else:
        return MessageResponse(message = f"PLL adjust FAILED: target: " + payload.getText(), success = False)

@router.put("/pll/clearunlock", response_model = MessageResponse)
async def clear_Unlock_Detect(request: Request):
    getTarget(request).clearUnlockDetect()
    return MessageResponse(message = "PLL cleared unlock detect.", success = True)

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
    if payload.loopBW is not None:
        getTarget(request).selectLoopBW(payload.loopBW)
    if payload.lockSB is not None:
        getTarget(request).selectLockSideband(payload.lockSB)
    return MessageResponse(message = f"PLL config " + payload.getText(), success = True)
    
@router.put("/pll/nullintegrator", response_model = MessageResponse)
async def setNullLoopIntegrator(request: Request, payload:SingleBool):
    getTarget(request).setNullLoopIntegrator(payload.value)
    return MessageResponse(message = "PLL null integrator " + payload.getText(), success = True)

@router.put("/photomixer/enable", response_model = MessageResponse)
async def set_Photmixer_Enable(request: Request, payload:SingleBool):
    getTarget(request).setPhotmixerEnable(payload.value)
    return MessageResponse(message = "Photomixer " + payload.getText(), success = True)

@router.put("/pa/bias", response_model = MessageResponse)
async def set_PA_Bias(request: Request, payload: SetPA):
    result = getTarget(request).setPABias(payload.pol, payload.VDControl, payload.VG)
    if result:
        return MessageResponse(message = "PA bias " + payload.getText(), success = True)
    else:
        return MessageResponse(message = "PA bias FAILED " + payload.getText(), success = False)
    
@router.put("/pa/teledyne", response_model = MessageResponse)
def set_Teledyne_PA_Config(request: Request, payload: TeledynePA):
    result = getTarget(request).setTeledynePAConfig(payload.hasTeledyne, payload.collectorP0, payload.collectorP1)
    if result:
        return MessageResponse(message = "Teledyne PA config " + payload.getText(), success = True)
    else:
        return MessageResponse(message = "Teledyne PA config FAILED " + payload.getText(), success = False)

@router.get("/yto", response_model = YTO)
async def get_YTO(request: Request):
    data = getTarget(request).getYTO()
    return YTO.parse_obj(data)
    
@router.get("/pll", response_model = PLL)
async def get_PLL(request: Request):
    data = getTarget(request).getPLL()
    return PLL.parse_obj(data)

@router.get("/pll/config", response_model = PLLConfig)
async def get_PLL_Config(request: Request):
    data = getTarget(request).getPLLConfig()
    return PLLConfig.parse_obj(data)

@router.get("/photomixer", response_model = Photomixer)
async def get_Photomixer(request: Request):
    data = getTarget(request).getPhotomixer()
    return Photomixer.parse_obj(data)

@router.get("/amc", response_model = AMC)
async def get_AMC(request: Request):
    data = getTarget(request).getAMC()
    return AMC.parse_obj(data)

@router.get("/pa", response_model = PA)
async def get_PA(request: Request):
    data = getTarget(request).getPA()
    return PA.parse_obj(data)

@router.get("/teledynepa", response_model = TeledynePA)
async def get_Teledyne_PA(request: Request):
    data = getTarget(request).getTeledynePA()
    return TeledynePA.parse_obj(data)
