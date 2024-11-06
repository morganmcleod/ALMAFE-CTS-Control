import configparser
from ALMAFE.database.DriverMySQL import DriverMySQL
from DBBand6Cart.LoadConfiguration import loadConfiguration
from DBBand6Cart.CartTests import CartTests

CTS_INI = 'ALMAFE-CTS-Control.ini'

def CTSDB():
    '''
    test and if necessary create the singleton CTSDatabaseAPI object
    '''
    try:
        return CTSDB.CTSDB
    except:
        CTSDB.CTSDB = DriverMySQL(loadConfiguration(CTS_INI, 'dbBand6Cart'))
        # https://stackoverflow.com/questions/11821976/cursor-fetchone-returns-none-but-row-in-the-database-exists
        CTSDB.CTSDB.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
        return CTSDB.CTSDB
    
def CartTestsDB():
    '''
    test and if necessary create the singleton CartTestsDB object
    '''
    try:
        return CartTestsDB.CartTestsDB
    except:
        config = configparser.ConfigParser()
        config.read(CTS_INI)
        try:
            fkCartTest = int(config['CartTests']['fkTestSystem'])
        except:
            fkCartTest = None
        CartTestsDB.CartTestsDB = CartTests(driver = CTSDB(), defaultFkTestSystem = fkCartTest)
        return CartTestsDB.CartTestsDB
   