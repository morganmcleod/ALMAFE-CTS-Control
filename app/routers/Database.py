from fastapi import APIRouter
from Response import ListResponse, prepareListResponse
router = APIRouter(prefix="/database")
from ALMAFE.database.DriverMySQL import DriverMySQL
from DBBand6Cart.CartConfigs import CartConfigs
from DBBand6Cart.LoadConfiguration import loadConfiguration

def CTSDB():
    '''
    test and if necessary create the CTSDatabaseAPI object
    '''
    try:
        CTSDB.CTSDB
    except:
        CTSDB.CTSDB = DriverMySQL(loadConfiguration('ALMAFE-CTS-Database.ini', 'dbBand6Cart'))
    return CTSDB.CTSDB

@router.get("/CCA6/config/", response_model = ListResponse)
async def getCCA6Configs(serialNum:int = None, configId:int = None, callback:str = None):
    '''
    Get the latest configuration for one or all CCA6 serial nums
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