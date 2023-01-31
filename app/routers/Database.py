from fastapi import APIRouter
from Response import ListResponse, prepareListResponse
router = APIRouter(prefix="/database")
from ALMAFE.database.DriverMySQL import DriverMySQL
from DBBand6Cart.LoadConfiguration import loadConfiguration
from DBBand6Cart.CartConfigs import CartConfigs
from DBBand6Cart.schemas.CartConfig import CartKeys
from DBBand6Cart.MixerParams import MixerParams
from DBBand6Cart.PreampParams import PreampParams

def CTSDB():
    '''
    test and if necessary create the CTSDatabaseAPI object
    '''
    try:
        CTSDB.CTSDB
    except:
        CTSDB.CTSDB = DriverMySQL(loadConfiguration('ALMAFE-CTS-Database.ini', 'dbBand6Cart'))
    return CTSDB.CTSDB

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
    items = DB.read(keyCartAssys = configId, serialNum = serialNum, latestOnly = False if serialNum else True)
    
    # prepare and return result:
    return prepareListResponse(items, callback)

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