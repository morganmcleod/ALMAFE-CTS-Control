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
        # https://stackoverflow.com/questions/11821976/cursor-fetchone-returns-none-but-row-in-the-database-exists
        CTSDB.CTSDB.cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
        return CTSDB.CTSDB
    