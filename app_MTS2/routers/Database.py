from typing import Optional
from fastapi import APIRouter
from app_Common.Response import ListResponse, prepareListResponse, MessageResponse
from app_Common.CTSDB import CTSDB
from app_Common.schemas.common import SingleBool
from DBBand6Cart.MixerConfigs import MixerConfigs
from DBBand6Cart.schemas.MixerConfig import MixerConfig, MixerKeys
from DBBand6Cart.MixerParams import MixerParam, MixerParams
from DBBand6Cart.PreampParams import PreampParam, PreampParams
from DBBand6Cart.schemas.WCA import WCA

import app_MTS2.hardware.MixerAssembly
mixerAssembly = app_MTS2.hardware.MixerAssembly.mixerAssembly
import app_MTS2.hardware.RFSource
rfSource = app_MTS2.hardware.RFSource.rfSource

mixerConfigsDB = MixerConfigs(driver = CTSDB())
mixerParamsDB = MixerParams(driver = CTSDB())
preampParamsDB = PreampParams(driver = CTSDB())

router = APIRouter(prefix="/database")

@router.get("/isconnected")
async def get_IsConnected():
    return SingleBool(value = CTSDB().is_connected())

@router.get("/configs", response_model = ListResponse)
async def getConfigs(
        serialNum:int = None, 
        configId:int = None
    ) -> list[MixerConfig]:
    '''
    Get the latest configuration for one or all mixer serial nums
    :param seraialNum: optional int
    :param configId: optional int
    :return list [MixerConfig] as prepared by prepareListResponse()
    '''
    # fetch configs from database:    
    items = mixerConfigsDB.read(configId, serialNum, latestOnly = False if serialNum else True)
    # prepare and return result:
    return prepareListResponse(items)

@router.put("/config/{configId}", response_model = MessageResponse)
async def putConfig(configId: int):
    if mixerAssembly.setConfig(configId):
        return MessageResponse(message = f"Selected mixer config {configId}", success = True)
    else:
        return MessageResponse(message = f"ERROR selecting mixer config {configId}", success = False)

@router.get("/config", response_model = Optional[MixerConfig])
async def getConfig():
    configId = mixerAssembly.getConfig()
    if not configId:
        return None
    return mixerConfigsDB.read(configId)[0]

@router.get("/config/keys", response_model = Optional[MixerKeys])
async def getConfigKeys(configId: int = None):
    if configId is None:
        configId =  mixerAssembly.getConfig()
    if not configId:
        return None
    else:
        return mixerConfigsDB.readKeys(configId)

@router.get("/config/mixer_params/{keyChip}", response_model = ListResponse)
async def getMixerParams(keyChip:int):
    items = mixerParamsDB.read(keyMixerChips = keyChip)    
    return prepareListResponse(items)

@router.put("/config/mixer_params/{keyChip}", response_model = MessageResponse)
async def putMixerParams(keyChip: int, values: list[MixerParam]):
    if mixerParamsDB.create(keyChip, values):
        return MessageResponse(message = f"Saved mixerparams for chip {keyChip}", success = True)
    else:
        return MessageResponse(message = f"Error writing mixerparams for chip {keyChip}", success = False)

@router.get("/config/preamp_params/{keyPreamp}", response_model = ListResponse)
async def getPreampParams(keyPreamp:int):
    items = preampParamsDB.read(keyPreamp = keyPreamp)
    return prepareListResponse(items)

@router.put("/config/preamp_params/{keyPreamp}", response_model = MessageResponse)
async def putPreampParams(keyPreamp:int, values: list[PreampParam]):
    if preampParamsDB.create(keyPreamp, values):
        return MessageResponse(message = f"Saved preampparams for amplifier {keyPreamp}", success = True)
    else:
        return MessageResponse(message = f"Error writing preampparams for amplifier {keyPreamp}", success = False)    

