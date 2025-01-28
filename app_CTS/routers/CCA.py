import yaml
from fastapi import APIRouter
from Controllers.schemas.MixerBias import *
from app_Common.schemas.common import *
from Controllers.schemas.DeviceInfo import DeviceInfo
from AMB.schemas.MixerTests import *
import hardware.FEMC as FEMC
from app_Common.Response import MessageResponse

router = APIRouter(prefix="/cca")

@router.get("/device_info", response_model = DeviceInfo)
async def get_DeviceInfo_CCA():
    return DeviceInfo(
        name = 'CCA',
        resource = "CAN0:13",
        connected = FEMC.ccaDevice.connected()
    )

@router.put("/sis", response_model = MessageResponse)
async def set_SIS(request: SetSIS):
    result = FEMC.ccaDevice.setSIS(request.pol, request.sis, request.Vj, request.Imag)
    if result:
        return MessageResponse(message = f"SIS settings: {request.getText()}", success = True)
    else:
        return MessageResponse(message = f"SIS setting FAILED: {request.getText()}", success = False)
    
@router.put("/sis/openloop", response_model = MessageResponse)
async def set_SIS_Open_Loop(request: SingleBool):
    FEMC.ccaDevice.setSISOpenLoop(request.value)
    return MessageResponse(message = "SIS open loop " + request.getText(), success = True)
    
@router.put("/sis/heater", response_model = MessageResponse)
async def set_SIS_Heater(pol: int, request: SingleBool):
    FEMC.ccaDevice.setSISHeater(pol, request.value)
    return MessageResponse(message = f"SIS heater pol{pol} " +  ("enabled." if request.value else "disabled."), success = True)

@router.put("/lna", response_model = MessageResponse)
async def set_LNA(request: SetLNA):
    result = FEMC.ccaDevice.setLNA(request.pol, request.lna, 
                                   request.VD1, request.VD2, request.VD3, request.VD4, request.VD5, request.VD6, 
                                   request.ID1, request.ID2, request.ID3, request.ID4, request.ID5, request.ID6)
    if result:
        return MessageResponse(message = "LNA bias: " + request.getText(), success = True)
    else:
        return MessageResponse(message = "LNA bias FAILED: " + request.getText(), success = False)    

@router.put("/lna/enable", response_model = MessageResponse)
async def set_LNA_Enable(request: SetLNAEnable):
    '''
    Enable/disable one, two, or all LNA devices
    :param pol:    int in 0,1 or both pols if -1
    :param lna:    int in 1,2 or both LNAs if -1
    :param enable: bool
    '''
    result = FEMC.ccaDevice.setLNAEnable(request.enable, request.pol, request.lna)
    polText = "1" if request.pol>=1 else ("both" if request.pol<=-1 else "0")
    lnaText = "2" if request.lna>=2 else ("both" if request.lna<=-1 else "1")
    enableText = "enabled" if request.enable else "disabled"
    if result:
        return MessageResponse(message = f"LNA {enableText} pol:{polText} lna:{lnaText} ", success = True)
    else:
        return MessageResponse(message = f"LNA set enable FAILED: pol:{polText} lna:{lnaText}", success = True)
    
@router.put("/lna/led", response_model = MessageResponse)
async def set_LNA_LED_Enable(request: SetLED):
    FEMC.ccaDevice.setLNALEDEnable(request.pol, request.enable)
    return MessageResponse(message = "LNA LED " + request.getText(), success = True)
    
@router.get("/tempsensors", response_model = Tempsensors)
async def get_Cartridge_Temps():
    data = FEMC.ccaDevice.getCartridgeTemps()
    return Tempsensors.parse_obj(data)
    
@router.get("/sis", response_model = SIS)
async def get_SIS(pol:int, sis:int, averaging:int = 1):
    data = FEMC.ccaDevice.getSIS(pol, sis, averaging)
    return SIS.parse_obj(data)
    
@router.get("/sis/openloop", response_model = SingleBool)
async def get_SIS_Open_Loop():
    data = FEMC.ccaDevice.getSISOpenLoop()
    return SingleBool(value = data)
    
@router.get("/lna", response_model = LNA)
async def get_LNA(pol:int, lna:int):
    data = FEMC.ccaDevice.getLNA(pol, lna)
    return LNA(pol = pol, lna = lna, enable = data['enable'],
               VD1=data['VD1'], VD2=data['VD2'], VD3=data['VD3'],
               ID1=data['ID1'], ID2=data['ID2'], ID3=data['ID3'],
               VG1=data['VG1'], VG2=data['VG2'], VG3=data['VG3'])
    
@router.get("/lna/led", response_model = SingleBool)
async def get_LNA_LED(pol:int):
    data = FEMC.ccaDevice.getLNALEDEnable(pol)
    return SingleBool(value = data)

@router.get("/sis/heater", response_model = SingleFloat)
async def get_Heater(pol: int):
    current = FEMC.ccaDevice.getSISHeaterCurrent(pol)
    return SingleFloat(value = current)

@router.put("/preset/{index}", response_model = MessageResponse)
async def put_Preset(index: int, preset:Preset):
    if index < 1 or index > 3:
        return MessageResponse(message = "Preset index out of range 1-3", success = False)
    else:
        with open(f"Settings/CCAPreset{index}.yaml", "w") as f:
            yaml.dump(preset.dict(), f)
        return MessageResponse(message = f"Saved preset '{preset.description}'", success = True)

@router.get("/preset/{index}", response_model = Preset)
async def get_Preset(index: int):
    if index <= 1 or index > 3:
        index = 1

    with open(f"Settings/CCAPreset{index}.yaml", "r") as f:
        d = yaml.safe_load(f)
    return Preset.parse_obj(d)
