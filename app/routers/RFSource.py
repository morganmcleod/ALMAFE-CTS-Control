from fastapi import APIRouter
from typing import Optional
from app.schemas.LO import *
import app.hardware.FEMC as FEMC
from app.Response import MessageResponse

router = APIRouter(prefix="/rfsource")

@router.put("/yto/limits/", tags=["RF source"], response_model = MessageResponse)
async def set_YTO_Limits(lowGhz:float, highGhz:float):
    FEMC.srcDevice.setYTOLimits(lowGhz, highGhz)
    return MessageResponse(message = f"YTO {lowGhz} to {highGhz} GHz", success = True)

@router.put("/yto/coursetune/", tags=["RF source"], response_model = MessageResponse)
async def set_YTO_CourseTune(courseTune:int):
    result = FEMC.srcDevice.setYTOCourseTune(courseTune)
    if result:
        return MessageResponse(message = f"YTO courseTune to {courseTune}", success = True)
    else:
        return MessageResponse(message = f"YTO courseTune FAILED: {courseTune}", success = False)

@router.put("/frequency/", tags=["RF source"], response_model = MessageResponse)
async def set_LO_Frequency(freqGHz:float, coldMultipler:Optional[int] = 1):
    (wcaFreq, ytoFreq, ytoCourse) = FEMC.srcDevice.setLOFrequency(freqGHz, coldMultipler)
    if wcaFreq:
        return MessageResponse(message = f"LO frequency set to {freqGHz} GHz [wcaFreq:{wcaFreq} ytoFreq:{ytoFreq} ytoCourse:{ytoCourse}]", 
                               success = True)
    else:
        return MessageResponse(message = f"LO frequency set FAILED: {freqGHz} GHz coldMultipler={coldMultipler}", 
                               success = False)

@router.put("/pll/lock/", tags=["RF source"], response_model = MessageResponse)
async def lock_PLL(freqLOGHz:float, coldMultipler:int = 1, freqFloogGhz:float = 0.0315):
    result = FEMC.srcDevice.lockPLL(freqLOGHz, coldMultipler, freqFloogGhz)
    wcaFreq = freqLOGHz / coldMultipler
    if result:
        return MessageResponse(message = f"PLL locked at {freqLOGHz} GHz [wcaFreq:{wcaFreq}]", success = True)
    else:
        return MessageResponse(message = f"PLL lock FAILED: {freqLOGHz} GHz [wcaFreq:{wcaFreq}]", success = False)

@router.put("/pll/adjust/", tags=["RF source"], response_model = MessageResponse)
async def adjust_PLL(targetCV:Optional[float] = 0):
    result = FEMC.srcDevice.adjustPLL(targetCV)
    if result:
        return MessageResponse(message = f"PLL adjusted for target CV {targetCV} V", success = True)
    else:
        return MessageResponse(message = f"PLL adjust FAILED: target CV {targetCV} V", success = False)

@router.put("/pll/clearunlock/", tags=["RF source"], response_model = MessageResponse)
async def clear_Unlock_Detect():
    FEMC.srcDevice.clearUnlockDetect()
    return MessageResponse(message = "PLL cleared unlock detect.", success = True)

@router.put("/pll/selectloopbw/", tags=["RF source"], response_model = MessageResponse)
async def select_Loop_BW(select:int = LoopBW.DEFAULT):
    '''
    select is one of:
    -1: Use the band's default loop bandwidth.
     0: Override to use the "normal" loop BW:   7.5MHz/V (Band 2,4,8,9).
     1: Override to use the "alternate" loop BW: 15MHz/V (Band 3,5,6,7,10, and NRAO band 2 prototype). 
    '''
    FEMC.srcDevice.selectLoopBW(select)
    return MessageResponse(message = f"PLL selected loop bandwidth: {select}.", success = True)
    
@router.put("/pll/selectlocksb/", tags=["RF source"], response_model = MessageResponse)
async def select_Lock_Sideband(select:int = LockSB.BELOW_REF):
    '''
    select is one of:
     0: Lock BELOW the reference input.
     1: Lock ABOVE the reference input. 
    '''
    FEMC.srcDevice.selectLockSideband(select)
    return MessageResponse(message = f"PLL selected lock sideband : {select}.", success = True)
    
@router.put("/pll/nullintegrator/", tags=["RF source"], response_model = MessageResponse)
async def setNullLoopIntegrator(enable:bool):
    FEMC.srcDevice.setNullLoopIntegrator(enable)
    return MessageResponse(message = "PLL null integrator" + ("enabled." if enable else "disabled."), success = True)

@router.put("/photomixer/enable/", tags=["RF source"], response_model = MessageResponse)
async def set_Photmixer_Enable(enable:bool):
    FEMC.srcDevice.setPhotmixerEnable(enable)
    return MessageResponse(message = "Photomixer " + ("enabled." if enable else "disabled."), success = True)

@router.put("/pa/bias/", tags=["RF source"], response_model = MessageResponse)
async def set_PA_Bias(pol:int, drainControl:float = None, gateVoltage:float = None):
    result = FEMC.srcDevice.setPABias(pol, drainControl, gateVoltage)
    drainText = f"{drainControl}" if drainControl else "no change"
    gateText = f"{gateVoltage}" if gateVoltage else "no change"
    if result:
        return MessageResponse(message = f"PA bias pol {pol}: drainControl={drainText} gateVoltage={gateText}", success = True)
    else:
        return MessageResponse(message = f"PA bias pol {pol} FAILED: drainControl={drainText} gateVoltage={gateText}", success = False)
    
@router.put("/pa/teledyne/", tags=["RF source"], response_model = MessageResponse)
def set_Teledyne_PA_Config(hasTeledyne:bool, collectorP0:int = 0, collectorP1:int = 0):
    result = FEMC.srcDevice.setTeledynePAConfig(hasTeledyne, collectorP0, collectorP1)
    if result:
        return MessageResponse(message = f"Teledyne PA config: hasTeledyne={hasTeledyne} collectorP0={collectorP0} collectorP1={collectorP1}",
                               success = True)
    else:
        return MessageResponse(message = f"Teledyne PA config FAILED: hasTeledyne={hasTeledyne} collectorP0={collectorP0} collectorP1={collectorP1}",
                               success = False)

@router.get("/yto/", tags=["RF source"], response_model = YTO)
async def get_YTO():
    data = FEMC.srcDevice.getYTO()
    result = YTO.parse_obj(data)
    return result
    
@router.get("/pll/", tags=["RF source"], response_model = PLL)
async def get_PLL():
    data = FEMC.srcDevice.getPLL()
    result = PLL.parse_obj(data)
    return result

@router.get("/pllconfig/", tags=["RF source"], response_model = PLLConfig)
async def get_PLL_Config():
    data = FEMC.srcDevice.getPLLConfig()
    result = PLLConfig.parse_obj(data)
    return result

@router.get("/photomixer/", tags=["RF source"], response_model = Photomixer)
async def get_Photomixer():
    data = FEMC.srcDevice.getPhotomixer()
    result = Photomixer.parse_obj(data)
    return result

@router.get("/amc/", tags=["RF source"], response_model = AMC)
async def get_AMC():
    data = FEMC.srcDevice.getAMC()
    result = AMC.parse_obj(data)
    return result

@router.get("/pa/", tags=["RF source"], response_model = PA)
async def get_PA():
    data = FEMC.srcDevice.getPA()
    result = PA.parse_obj(data)
    return result

@router.get("/teledynepa/", tags=["RF source"], response_model = TeledynePA)
async def get_Teledyne_PA():
    data = FEMC.srcDevice.getTeledynePA()
    result = TeledynePA.parse_obj(data)
    return result
