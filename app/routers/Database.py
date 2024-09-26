from fastapi import APIRouter
from app.schemas.Response import ListResponse, prepareListResponse, MessageResponse
router = APIRouter(prefix="/database")

from app.database.CTSDB import CTSDB
from schemas.common import SingleBool
from DBBand6Cart.CartConfigs import CartConfig, CartConfigs
from DBBand6Cart.schemas.CartConfig import CartKeys
from DBBand6Cart.MixerParams import MixerParam, MixerParams
from DBBand6Cart.PreampParams import PreampParam, PreampParams
from DBBand6Cart.WCAs import WCAs, WCA
from typing import Optional, List
from hardware.FEMC import cartAssembly, rfSrcDevice

@router.get("/isconnected")
async def get_IsConnected():
    return SingleBool(value = CTSDB().is_connected())

@router.get("/configs", response_model = ListResponse)
async def getConfigs(serialNum:int = None, configId:int = None, callback:str = None):
    '''
    Get the latest configuration for one or all cartridge serial nums
    :param seraialNum: optional int
    :param configId: optional int
    :param callback: optional name of Javascript function to wrap JSONP results in.
    :return list [CartConfig] as prepared by prepareListResponse()
    '''
    # fetch configs from database:
    DB = CartConfigs(driver = CTSDB())
    items = DB.read(keyColdCart = configId, serialNum = serialNum, latestOnly = False if serialNum else True)
    
    # prepare and return result:
    return prepareListResponse(items, callback)

@router.put("/config/{configId}", response_model = MessageResponse)
async def putCartConfig(configId: int):
    if cartAssembly.setConfig(configId):
        return MessageResponse(message = f"Selected cartridge config {configId}", success = True)
    else:
        return MessageResponse(message = f"ERROR selecting cartridge config {configId}", success = False)

@router.get("/config", response_model = Optional[CartConfig])
async def getCartConfig():
    configId = cartAssembly.getConfig()
    if not configId:
        return None

    DB = CartConfigs(driver = CTSDB())
    return DB.read(configId)[0]

@router.put("/lo/config/{configId}", response_model = MessageResponse)
async def putLOConfig(configId: int):
    if cartAssembly.setLOConfig(configId):
        return MessageResponse(message = f"Selected LO config {configId}", success = True)
    else:
        return MessageResponse(message = f"ERROR selecting LO config {configId}", success = False)

@router.get("/lo/config", response_model = WCA)
async def getLOConfiig():
    return cartAssembly.getLOConfig()

@router.put("/rfsource/config/{configId}", response_model = MessageResponse)
async def putRFSourceConfig(configId: int):
    if rfSrcDevice.setRFSourceConfig(configId):
        return MessageResponse(message = f"Selected RF source config {configId}", success = True)
    else:
        return MessageResponse(message = f"ERROR selecting RF source config {configId}", success = False)

@router.get("/rfsource/config", response_model = WCA)
async def getRFSrcConfiig():
    return rfSrcDevice.getRFSourceConfig()

@router.get("/config/keys", response_model = Optional[CartKeys])
async def getConfigKeys(configId:int, pol:int, callback:str = None):
    DB = CartConfigs(driver = CTSDB())
    return DB.readKeys(configId, pol)

@router.get("/config/mixer_params/{keyChip}", response_model = ListResponse)
async def getMixerParams(keyChip:int, callback:str = None):
    DB = MixerParams(driver = CTSDB())
    items = DB.read(keyMixerChips = keyChip)
    
    # prepare and return result:
    return prepareListResponse(items, callback)

@router.put("/config/mixer_params/{keyChip}", response_model = MessageResponse)
async def putMixerParams(keyChip: int, values: List[MixerParam], callback:str = None):
    DB = MixerParams(driver = CTSDB())
    if DB.create(keyChip, values):
        return MessageResponse(message = f"Saved mixerparams for chip {keyChip}", success = True)
    else:
        return MessageResponse(message = f"Error writing mixerparams for chip {keyChip}", success = False)

@router.get("/config/preamp_params/{keyPreamp}", response_model = ListResponse)
async def getPreampParams(keyPreamp:int, callback:str = None):
    DB = PreampParams(driver = CTSDB())
    items = DB.read(keyPreamp = keyPreamp)
    
    # prepare and return result:
    return prepareListResponse(items, callback)

@router.put("/config/preamp_params/{keyPreamp}", response_model = MessageResponse)
async def putPreampParams(keyPreamp:int, values: List[PreampParam], callback:str = None):
    DB = PreampParams(driver = CTSDB())
    if DB.create(keyPreamp, values):
        return MessageResponse(message = f"Saved preampparams for amplifier {keyPreamp}", success = True)
    else:
        return MessageResponse(message = f"Error writing preampparams for amplifier {keyPreamp}", success = False)    

@router.get("/config/wcas", response_model = ListResponse)
async def getWCAs(prefix: str = None, callback:str = None):
    DB = WCAs(driver = CTSDB())
    items = DB.read(serialNumLike = prefix + '%' if prefix else None)
    return prepareListResponse(items, callback)
