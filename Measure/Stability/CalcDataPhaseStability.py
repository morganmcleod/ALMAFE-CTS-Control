from .CalcDataInterface import CalcDataInterface, StabilityRecord
from DBBand6Cart.PhaseStability import PhaseStability
from DBBand6Cart.schemas.PhaseStabilityRecord import PhaseStabilityRecord
from ALMAFE.database.DriverMySQL import DriverMySQL
from typing import List, Tuple

class CalcDataPhaseStability(CalcDataInterface):
    def __init__(self, connectionInfo:dict = None, driver:DriverMySQL = None):
        """ Constructor
        
        :param connectionInfo: for initializing DriverMySQL if driver is not provided
        :param driver: initialized DriverMySQL to use or None
        """
        super(CalcDataPhaseStability, self).__init__()
        self.DB = PhaseStability(connectionInfo, driver)

    def create(self, records: List[StabilityRecord]) -> Tuple[bool, str]:
        """ Create phase stability records"""
        phaseRecords = [PhaseStabilityRecord(
            fkCartTest = rec.fkCartTest,
            fkRawData = rec.fkRawData,
            freqLO = rec.freqLO,
            freqCarrier = rec.freqCarrier,
            pol = rec.pol,
            sideband = rec.sideband,
            time = rec.time,
            allanDev = rec.allan,
            errorBar = rec.errorBar
        ) for rec in records]

        if not self.DB.create(phaseRecords):
            return False, "CalcDataAmplitudeStability: Error creating phase stability records"
        else:
            return True, ""
