from .CalcDataInterface import CalcDataInterface, StabilityRecord
from DBBand6Cart.AmplitudeStability import AmplitudeStability
from DBBand6Cart.schemas.AmplitudeStabilityRecord import AmplitudeStabilityRecord
from ALMAFE.database.DriverMySQL import DriverMySQL
from typing import List, Tuple

class CalcDataAmplitudeStability(CalcDataInterface):
    def __init__(self, connectionInfo:dict = None, driver:DriverMySQL = None):
        """ Constructor
        
        :param connectionInfo: for initializing DriverMySQL if driver is not provided
        :param driver: initialized DriverMySQL to use or None
        """
        self.DB = AmplitudeStability(connectionInfo, driver)

    def create(self, records: List[StabilityRecord]) -> Tuple[bool, str]:
        """ Create amplitude stability records"""
        ampRecords = [AmplitudeStabilityRecord(
            fkCartTest = rec.fkCartTest,
            fkRawData = rec.fkRawData,
            freqLO = rec.freqLO,
            pol = rec.pol,
            sideband = rec.sideband,
            time = rec.time,
            allanVar = rec.allan,
            errorBar = rec.errorBar
        ) for rec in records]

        if not self.DB.create(ampRecords):
            return False, "CalcDataAmplitudeStability: Error createing amplitude stability records"
        else:
            return True, ""
