from fastapi import APIRouter, Request
from schemas.LO import *
from schemas.common import *
from Response import MessageResponse
import hardware.FEMC as FEMC

router = APIRouter()
router.hardwareDevice = FEMC.loDevice
router.name = "LO"

@router.get("/connected", response_model = SingleBool)
async def get_isConnected(request: Request):
    return SingleBool(value = router.hardwareDevice.isConnected())

@router.put("/yto/limits", response_model = MessageResponse)
async def set_YTO_Limits(request: Request, payload: ConfigYTO):
    router.hardwareDevice.setYTOLimits(payload.lowGHz, payload.highGHz)
    return MessageResponse(message = f"{router.name} YTO: " + payload.getText(), success = True)

@router.put("/yto/coursetune", response_model = MessageResponse)
async def set_YTO_CourseTune(request: Request, payload: SetYTO):
    result = router.hardwareDevice.setYTOCourseTune(payload.courseTune)
    if result:
        return MessageResponse(message = f"{router.name} YTO courseTune " + payload.getText(), success = True)
    else:
        return MessageResponse(message = f"{router.name} YTO courseTune FAILED: " + payload.getText(), success = False)

@router.put("/frequency", response_model = MessageResponse)
async def set_Frequency(request: Request, payload: SetLOFrequency):
    (wcaFreq, ytoFreq, ytoCourse) = router.hardwareDevice.setLOFrequency(payload.freqGHz)
    if wcaFreq:
        wcaText = f" [wcaFreq:{wcaFreq} ytoFreq:{ytoFreq} ytoCourse:{ytoCourse}]"
        return MessageResponse(message = f"{router.name} frequency " + payload.getText() + wcaText, success = True)
    else:
        return MessageResponse(message = f"{router.name} frequency FAILED: " + payload.getText(), success = False)

@router.put("/pll/lock", response_model = MessageResponse)
async def lock_PLL(request: Request, payload: LockPLL):
    (wcaFreq, ytoFreq, ytoCourse) = router.hardwareDevice.lockPLL(payload.freqLOGHz)
    if wcaFreq:
        wcaText = f" [wcaFreq:{wcaFreq} ytoFreq:{ytoFreq} ytoCourse:{ytoCourse}]"
        return MessageResponse(message = f"{router.name} PLL LOCKED " + payload.getText() + wcaText, success = True)
    else:
        return MessageResponse(message = f"{router.name} PLL lock FAILED " + payload.getText(), success = False)

@router.put("/pll/adjust", response_model = MessageResponse)
async def adjust_PLL(request: Request, payload: AdjustPLL):
    CV = router.hardwareDevice.adjustPLL(payload.router.hardwareDeviceCV)
    if CV is not None:
        return MessageResponse(message = f"{router.name} PLL adjusted CV:{CV} router.hardwareDevice: {payload.getText()}", success = True)
    else:
        return MessageResponse(message = f"{router.name} PLL adjust FAILED: router.hardwareDevice: {payload.getText()}", success = False)

@router.put("/pll/clearunlock", response_model = MessageResponse)
async def clear_Unlock_Detect(request: Request):
    router.hardwareDevice.clearUnlockDetect()
    return MessageResponse(message = f"{router.name} PLL cleared unlock detect.", success = True)

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
    router.hardwareDevice, name = selectLODevice(request)
    assert(router.hardwareDevice)
    if payload.loopBW is not None:
        router.hardwareDevice.selectLoopBW(payload.loopBW)
    if payload.lockSB is not None:
        router.hardwareDevice.selectLockSideband(payload.lockSB)
    return MessageResponse(message = f"{router.name} PLL config " + payload.getText(), success = True)
    
@router.put("/pll/nullintegrator", response_model = MessageResponse)
async def setNullLoopIntegrator(request: Request, payload:SingleBool):
    router.hardwareDevice.setNullLoopIntegrator(payload.value)
    return MessageResponse(message = f"{router.name} PLL null integrator " + payload.getText(), success = True)

@router.put("/photomixer/enable", response_model = MessageResponse)
async def set_Photmixer_Enable(request: Request, payload:SingleBool):
    router.hardwareDevice.setPhotmixerEnable(payload.value)
    return MessageResponse(message = f"{router.name} Photomixer " + payload.getText(), success = True)

@router.put("/pa/bias", response_model = MessageResponse)
async def set_PA_Bias(request: Request, payload: SetPA):
    result = router.hardwareDevice.setPABias(payload.pol, payload.VDControl, payload.VG)
    if result:
        return MessageResponse(message = f"{router.name} PA bias " + payload.getText(), success = True)
    else:
        return MessageResponse(message = f"{router.name} PA bias FAILED " + payload.getText(), success = False)
    
@router.put("/pa/teledyne", response_model = MessageResponse)
def set_Teledyne_PA_Config(request: Request, payload: TeledynePA):
    result = router.hardwareDevice.setTeledynePAConfig(payload.hasTeledyne, payload.collectorP0, payload.collectorP1)
    if result:
        return MessageResponse(message = f"{router.name} Teledyne PA config " + payload.getText(), success = True)
    else:
        return MessageResponse(message = f"{router.name} Teledyne PA config FAILED " + payload.getText(), success = False)

@router.get("/yto", response_model = YTO)
async def get_YTO(request: Request):
    data = router.hardwareDevice.getYTO()
    return YTO.parse_obj(data)
    
@router.get("/pll", response_model = PLL)
async def get_PLL(request: Request):
    data = router.hardwareDevice.getPLL()
    return PLL.parse_obj(data)

@router.get("/pll/lock", response_model = LockInfo)
async def get_PLL_lockinfo(request: Request):
    data = router.hardwareDevice.getLockInfo()
    return LockInfo.parse_obj(data)

@router.get("/pll/config", response_model = PLLConfig)
async def get_PLL_Config(request: Request):
    data = router.hardwareDevice.getPLLConfig()
    return PLLConfig.parse_obj(data)

@router.get("/photomixer", response_model = Photomixer)
async def get_Photomixer(request: Request):
    data = router.hardwareDevice.getPhotomixer()
    return Photomixer.parse_obj(data)

@router.get("/amc", response_model = AMC)
async def get_AMC(request: Request):
    data = router.hardwareDevice.getAMC()
    return AMC.parse_obj(data)

@router.get("/pa", response_model = PA)
async def get_PA(request: Request):
    data = router.hardwareDevice.getPA()
    return PA.parse_obj(data)

@router.get("/teledynepa", response_model = TeledynePA)
async def get_Teledyne_PA(request: Request):
    data = router.hardwareDevice.getTeledynePA()
    return TeledynePA.parse_obj(data)
