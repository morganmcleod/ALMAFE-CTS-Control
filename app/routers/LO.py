from fastapi import APIRouter
from schemas.LO import *
from schemas.common import *
import hardware.FEMC as FEMC
from Response import MessageResponse

router = APIRouter(prefix="/lo")

@router.put("/yto/limits", tags=["LO"], response_model = MessageResponse)
async def set_YTO_Limits(request: ConfigYTO):
    FEMC.loDevice.setYTOLimits(request.lowGHz, request.highGHz)
    return MessageResponse(message = "YTO: " + request.getText(), success = True)

@router.put("/yto/coursetune", tags=["LO"], response_model = MessageResponse)
async def set_YTO_CourseTune(request: SetYTO):
    result = FEMC.loDevice.setYTOCourseTune(request.courseTune)
    if result:
        return MessageResponse(message = "YTO courseTune " + request.getText(), success = True)
    else:
        return MessageResponse(message = "YTO courseTune FAILED: " + request.getText(), success = False)

@router.put("/frequency", tags=["LO"], response_model = MessageResponse)
async def set_LO_Frequency(request: SetLOFrequency):
    (wcaFreq, ytoFreq, ytoCourse) = FEMC.loDevice.setLOFrequency(request.freqGHz)
    if wcaFreq:
        wcaText = f" [wcaFreq:{wcaFreq} ytoFreq:{ytoFreq} ytoCourse:{ytoCourse}]"
        return MessageResponse(message = "LO frequency " + request.getText() + wcaText, success = True)
    else:
        return MessageResponse(message = "LO frequency FAILED: " + request.getText(), success = False)

@router.put("/pll/lock", tags=["LO"], response_model = MessageResponse)
async def lock_PLL(request:LockPLL):
    (wcaFreq, ytoFreq, ytoCourse) = FEMC.loDevice.lockPLL(request.freqLOGHz, request.freqFloogGHz)
    if wcaFreq:
        wcaText = f" [wcaFreq:{wcaFreq} ytoFreq:{ytoFreq} ytoCourse:{ytoCourse}]"
        return MessageResponse(message = "PLL LOCKED " + request.getText() + wcaText, success = True)
    else:
        return MessageResponse(message = "PLL lock FAILED " + request.getText(), success = False)

@router.put("/pll/adjust", tags=["LO"], response_model = MessageResponse)
async def adjust_PLL(request: AdjustPLL):
    CV = FEMC.loDevice.adjustPLL(request.targetCV)
    if CV is not None:
        return MessageResponse(message = f"PLL adjusted CV:{CV} [target:" + request.getText + "]", success = True)
    else:
        return MessageResponse(message = f"PLL adjust FAILED: target: " + request.getText(), success = False)

@router.put("/pll/clearunlock", tags=["LO"], response_model = MessageResponse)
async def clear_Unlock_Detect():
    FEMC.loDevice.clearUnlockDetect()
    return MessageResponse(message = "PLL cleared unlock detect.", success = True)

@router.put("/pll/config", tags=["LO"], response_model = MessageResponse)
async def set_PLL_Config(request: PLLConfig):
    '''
    request.loopBW is one of:
    -1: Use the band's default loop bandwidth.
     0: Override to use the "normal" loop BW:   7.5MHz/V (Band 2,4,8,9).
     1: Override to use the "alternate" loop BW: 15MHz/V (Band 3,5,6,7,10, and NRAO band 2 prototype).
     None/null: no change 
    request.lockSB is one of:
     0: Lock BELOW the reference input.
     1: Lock ABOVE the reference input. 
     None/null: no change 
    '''
    if request.loopBW is not None:
        FEMC.loDevice.selectLoopBW(request.loopBW)
    if request.lockSB is not None:
        FEMC.loDevice.selectLockSideband(request.lockSB)
    return MessageResponse(message = f"PLL config " + request.getText(), success = True)
    
@router.put("/pll/nullintegrator", tags=["LO"], response_model = MessageResponse)
async def setNullLoopIntegrator(request:SingleBool):
    FEMC.loDevice.setNullLoopIntegrator(request.enable)
    return MessageResponse(message = "PLL null integrator " + request.getText(), success = True)

@router.put("/photomixer/enable", tags=["LO"], response_model = MessageResponse)
async def set_Photmixer_Enable(request:SingleBool):
    FEMC.loDevice.setPhotmixerEnable(request.enable)
    return MessageResponse(message = "Photomixer " + request.getText(), success = True)

@router.put("/pa/bias", tags=["LO"], response_model = MessageResponse)
async def set_PA_Bias(request: SetPA):
    result = FEMC.loDevice.setPABias(request.pol, request.VDControl, request.VG)
    if result:
        return MessageResponse(message = "PA bias " + request.getText(), success = True)
    else:
        return MessageResponse(message = "PA bias FAILED " + request.getText(), success = False)
    
@router.put("/pa/teledyne", tags=["LO"], response_model = MessageResponse)
def set_Teledyne_PA_Config(request: TeledynePA):
    result = FEMC.loDevice.setTeledynePAConfig(request.hasTeledyne, request.collectorP0, request.collectorP1)
    if result:
        return MessageResponse(message = "Teledyne PA config " + request.getText(), success = True)
    else:
        return MessageResponse(message = "Teledyne PA config FAILED " + request.getText(), success = False)

@router.get("/yto", tags=["LO"], response_model = YTO)
async def get_YTO():
    data = FEMC.loDevice.getYTO()
    return YTO.parse_obj(data)
    
@router.get("/pll", tags=["LO"], response_model = PLL)
async def get_PLL():
    data = FEMC.loDevice.getPLL()
    return PLL.parse_obj(data)

@router.get("/pll/config", tags=["LO"], response_model = PLLConfig)
async def get_PLL_Config():
    data = FEMC.loDevice.getPLLConfig()
    return PLLConfig.parse_obj(data)

@router.get("/photomixer", tags=["LO"], response_model = Photomixer)
async def get_Photomixer():
    data = FEMC.loDevice.getPhotomixer()
    return Photomixer.parse_obj(data)

@router.get("/amc", tags=["LO"], response_model = AMC)
async def get_AMC():
    data = FEMC.loDevice.getAMC()
    return AMC.parse_obj(data)

@router.get("/pa", tags=["LO"], response_model = PA)
async def get_PA():
    data = FEMC.loDevice.getPA()
    return PA.parse_obj(data)

@router.get("/teledynepa", tags=["LO"], response_model = TeledynePA)
async def get_Teledyne_PA():
    data = FEMC.loDevice.getTeledynePA()
    return TeledynePA.parse_obj(data)
