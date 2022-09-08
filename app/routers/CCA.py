from fastapi import APIRouter
from typing import Optional, Any
from app.schemas.CCA import *
import app.hardware.FEMC as FEMC
from app.Response import MessageResponse

router = APIRouter(prefix="/cca")

@router.put("/cca/sis/", tags=["CCA"], response_model = MessageResponse)
async def set_SIS(pol:int, sis:int, Vj:Optional[float] = None, Imag:Optional[float] = None):
    result = FEMC.ccaDevice.setSIS(pol, sis, Vj, Imag)
    valText = f"Vj={Vj}" if Vj else ""
    valText += " " if valText else ""
    valText += f"Imag={Imag}" if Imag else ""
    if result:
        return MessageResponse(message = f"SIS settings: {valText}", success = True)
    else:
        return MessageResponse(message = f"SIS setting FAILED: {valText}", success = False)
    
@router.put("/cca/sisopenloop/", tags=["CCA"], response_model = MessageResponse)
async def set_SIS_Open_Loop(openLoop:bool = False):
    FEMC.ccaDevice.setSISOpenLoop(openLoop)
    return MessageResponse(message = "SIS open loop " +  ("enabled." if openLoop else "disabled."), success = True)
    
@router.put("/cca/sisheater/", tags=["CCA"], response_model = MessageResponse)
async def set_SIS_Heater(enable:bool):
    FEMC.ccaDevice.setSISHeater(enable)
    return MessageResponse(message = "SIS heater " +  ("enabled." if enable else "disabled."), success = True)
    
@router.put("/cca/lnaenable/", tags=["CCA"], response_model = MessageResponse)
async def set_LNA_Enable(enable:bool, pol:int = -1, lna:int = -1):
    '''
    Enable/disable one, two, or all LNA devices
    :param pol:    int in 0,1 or both pols if -1
    :param lna:    int in 1,2 or both LNAs if -1
    :param enable: bool
    '''
    result = FEMC.ccaDevice.setLNAEnable(enable, pol, lna)
    polText = "1" if pol>=1 else ("both" if pol<=-1 else "0")
    lnaText = "2" if lna>=2 else ("both" if lna<=-1 else "1")
    enableText = "enabled" if enable else "disabled"
    if result:
        return MessageResponse(message = f"LNA {enableText} pol:{polText} lna:{lnaText} ", success = True)
    else:
        return MessageResponse(message = f"LNA set enable FAILED: pol:{polText} lna:{lnaText}", success = True)

@router.put("/cca/lna/", tags=["CCA"], response_model = MessageResponse)
async def set_LNA(pol:int, lna:int, bias:LNABias):
    result = FEMC.ccaDevice.setLNA(pol, lna, 
                                   bias.VD1, bias.VD2, bias.VD3, bias.VD4, bias.VD5, bias.VD6, 
                                   bias.ID1, bias.ID2, bias.ID3, bias.ID4, bias.ID5, bias.ID6)
    if result:
        return MessageResponse(message = "LNA bias: " + bias.getText(), success = True)
    else:
        return MessageResponse(message = "LNA bias FAILED: " + bias.getText(), success = False)
    
@router.put("/cca/lnaled/", tags=["CCA"], response_model = MessageResponse)
async def set_LNA_LED_Enable(enable:bool):
    FEMC.ccaDevice.setLNALEDEnable(enable)
    return MessageResponse(message = "LNA LED " +  ("enabled." if enable else "disabled."), success = True)
    
@router.get("/cca/tempsensors/", tags=["CCA"], response_model = Tempsensors)
async def get_Cartridge_Temps():
    data = FEMC.ccaDevice.getCartridgeTemps()
    result = Tempsensors.parse_obj(data)
    return result
    
@router.get("/cca/sis/", tags=["CCA"], response_model = SIS)
async def get_SIS(pol:int, sis:int, averaging:int = 1):
    data = FEMC.ccaDevice.getSIS(pol, sis, averaging)
    result = SIS.parse_obj(data)
    return result
    
@router.get("/cca/sisopenloop/", tags=["CCA"], response_model = SISOpenLoop)
async def get_SIS_Open_Loop():
    data = FEMC.ccaDevice.getSISOpenLoop()
    result = SISOpenLoop(enable = data)
    return result
    
@router.get("/cca/lna/", tags=["CCA"], response_model = LNA)
async def get_LNA(pol:int, lna:int):
    data = FEMC.ccaDevice.getLNA(pol, lna)
    result = LNA.parse_obj(data)
    return result 
    
@router.get("/cca/heatercurrent/", tags=["CCA"], response_model = Heater)
async def get_Heater_Current():
    data = FEMC.ccaDevice.getHeaterCurrent()
    result = Heater(current = data)
    return result
