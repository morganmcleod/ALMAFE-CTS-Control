from ALMAFE.database.DriverMySQL import DriverMySQL
from DBBand6Cart.LoadConfiguration import loadConfiguration

def CTSDB():
    '''
    test and if necessary create the CTSDatabaseAPI object
    '''
    try:
        return CTSDB.CTSDB
    except:
        CTSDB.CTSDB = DriverMySQL(loadConfiguration('ALMAFE-CTS-Database.ini', 'dbBand6Cart'))
        return CTSDB.CTSDB
    