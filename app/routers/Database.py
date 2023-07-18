from fastapi import APIRouter
from Response import ListResponse, prepareListResponse, MessageResponse
router = APIRouter(prefix="/database")

from app.database.CTSDB import CTSDB

from DBBand6Cart.CartConfigs import CartConfigs
from DBBand6Cart.schemas.CartConfig import CartKeys
from DBBand6Cart.MixerParams import MixerParams
from DBBand6Cart.PreampParams import PreampParams

from hardware.FEMC import cartAssembly

@router.get("/config/", response_model = ListResponse)
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
async def putCartConfig(configId:int):
    if cartAssembly.setConfig(configId):
        return MessageResponse(message = f"Selected cartridge config {configId}", success = True)
    else:
        return MessageResponse(message = f"ERROR selecting cartridge config {configId}", success = False)

@router.get("/config/keys/", response_model = CartKeys)
async def getConfigKeys(configId:int, pol:int, callback:str = None):
    DB = CartConfigs(driver = CTSDB())
    return DB.readKeys(configId, pol)

@router.get("/config/mixer_params/", response_model = ListResponse)
async def getMixerParams(keyChip:int, callback:str = None):
    DB = MixerParams(driver = CTSDB())
    items = DB.read(keyMixerChips = keyChip)
    
    # prepare and return result:
    return prepareListResponse(items, callback)

@router.get("/config/preamp_params/", response_model = ListResponse)
async def getPreampParams(keyPreamp:int, callback:str = None):
    DB = PreampParams(driver = CTSDB())
    items = DB.read(keyPreamp = keyPreamp)
    
    # prepare and return result:
    return prepareListResponse(items, callback)