import asyncio
import logging
import yaml
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app_Common.Response import MessageResponse
from app_Common.ConnectionManager import ConnectionManager
from Controllers.schemas.MixerBias import *
from app_Common.schemas.common import *
from Controllers.schemas.DeviceInfo import DeviceInfo
from Measure.Shared.SelectSIS import SelectSIS
from Controllers.LNA.Interface import SelectLNA
from DBBand6Cart.schemas.PreampParam import PreampParam

import app_MTS2.hardware.MixerAssembly
mixerAssembly = app_MTS2.hardware.MixerAssembly.mixerAssembly

logger = logging.getLogger("ALMAFE-CTS-Control")
router = APIRouter(prefix="/mixerassy")
manager = ConnectionManager()

@router.websocket("/auto_lo/current_ws")
async def websocket_sis_current(websocket: WebSocket):
    await manager.connect(websocket)
    last_measured = None
    try:
        while True:
            status = mixerAssembly.getAutoLOStatus()
            if status.is_active and status.last_measured != last_measured:
                last_measured = status.last_measured
                await manager.send(status.last_measured, websocket)     
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocketDisconnect: /auto_lo/current_ws")

@router.put("/auto_lo", response_model = MessageResponse)
async def put_AutoLOPower():
    if not mixerAssembly.autoLOPower(on_thread = True):
        return MessageResponse(message = "Auto LO power failed", success = False)
    else:
        return MessageResponse(message = "Setting auto LO power...", success = True)

@router.get("/device_info", response_model = DeviceInfo)
async def get_DeviceInfo():
    return mixerAssembly.getDeviceInfo()

@router.put("/sis", response_model = MessageResponse)
async def set_SIS(request: SetSIS):
    try:
        select = SelectSIS(request.sis)
        if request.Vj is not None:
            mixerAssembly.sisBias.set_bias(select, request.Vj)
        if request.Imag is not None:
            mixerAssembly.sisMagnet.setCurrent(request.Imag)
        return MessageResponse(message = f"SIS settings: {request.getText()}", success = True)
    except:
        pass
    return MessageResponse(message = f"SIS setting FAILED: {request.getText()}", success = False)

@router.get("/sis", response_model = SIS)
async def get_SIS(sis:int, averaging:int = 1):
    try:
        select = SelectSIS(sis)
        Vj, Ij = mixerAssembly.sisBias.read_bias(select, averaging)
        if select == SelectSIS.SIS1:
            Imag = mixerAssembly.sisMagnet.readCurrent(averaging)
        else:
            Imag = 0
        return SIS(
            Vj = Vj,
            Ij = Ij,
            Imag = Imag,
            Vmag = 0,
            averaging = averaging
        )
    except Exception as e:
        return None

@router.put("/lna", response_model = MessageResponse)
async def set_LNA(request: SetLNA):
    try:
        select = SelectLNA(request.lna)
        success = mixerAssembly.lnaBias.set_bias(
            select, 
            PreampParam(
                VD1 = request.VD1,
                VD2 = request.VD2,
                VD3 = request.VD3,
                ID1 = request.ID1,
                ID2 = request.ID2,
                ID3 = request.ID3
            )
        )        
        if success:
            return MessageResponse(message = "LNA bias: " + request.getText(), success = True)
    except Exception as e:
        pass
    return MessageResponse(message = "LNA bias FAILED: " + request.getText(), success = False)    

@router.put("/lna/enable", response_model = MessageResponse)
async def set_LNA_Enable(request: SetLNAEnable):
    '''
    Enable/disable one, two, or all LNA devices
    :param request: SetLNAEnable struct
    :param lna:    int in 1,2 or both LNAs if -1
    :param enable: bool
    '''
    enableText = "enabled" if request.enable else "disabled"
    try:
        select = SelectLNA(request.lna)
        success, msg = mixerAssembly.lnaBias.set_enable(select, request.enable)
        if success:
            return MessageResponse(message = f"LNA {enableText}", success = True)
    except:
        pass
    return MessageResponse(message = f"LNA {enableText} FAILED", success = True)
  
@router.get("/lna", response_model = LNA)
async def get_LNA(lna: int):
    try:
        select = SelectLNA(lna)
        data = mixerAssembly.lnaBias.read_bias(select)
        return LNA(
            lna = lna, 
            enable = data['enable'],
            VD1=data['VD1'], VD2=data['VD2'], VD3=data['VD3'],
            ID1=data['ID1'], ID2=data['ID2'], ID3=data['ID3'],
            VG1=data['VG1'], VG2=data['VG2'], VG3=data['VG3']
        )
    except:
        return None

@router.put("/preset/{index}", response_model = MessageResponse)
async def put_Preset(index: int, preset:Preset):
    if index < 1 or index > 3:
        return MessageResponse(message = "Preset index out of range 1-3", success = False)
    else:
        with open(f"Settings/CCAPreset{index}.yaml", "w") as f:
            yaml.dump(preset.model_dump(), f)
        return MessageResponse(message = f"Saved preset '{preset.description}'", success = True)

@router.get("/preset/{index}", response_model = Preset)
async def get_Preset(index: int):
    if index <= 1 or index > 3:
        index = 1
    with open(f"Settings/CCAPreset{index}.yaml", "r") as f:
        d = yaml.safe_load(f)
    return Preset.model_validate(d)
