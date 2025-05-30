from datetime import datetime
import app_Common.measProcedure.MeasurementStatus
import app_Common.measProcedure.DataDisplay
import app_CTS.measProcedure.Stability
import hardware.ReferenceSources
import hardware.FEMC
import hardware.Stability
import hardware.PowerDetect
import hardware.IFSystem
import hardware.BeamScanner
import hardware.NoiseTemperature
from Controllers.PowerDetect.PDPNA import PDPNA
from Controllers.PowerDetect.PDVoltMeter import PDVoltMeter
from database.CTSDB import CTSDB
from Measure.Shared.makeSteps import makeSteps
from Measure.Shared.SelectPolarization import SelectPolarization
from Measure.Shared.SelectSideband import SelectSideband
from DBBand6Cart.schemas.DUT_Type import DUT_Type
from DBBand6Cart.schemas.TestType import TestTypeIds
from DBBand6Cart.TestResults import DataStatus, TestResult, TestResults
from DBBand6Cart.TestResultPlots import TestResultPlot, TestResultPlots
from app_Common.CTSDB import CartTestsDB
from AmpPhaseDataLib.TimeSeriesAPI import TimeSeriesAPI
from AmpPhaseDataLib.TimeSeries import TimeSeries
from AmpPhaseDataLib.Constants import Units, DataSource, SpecLines, DataKind, PlotEl, StabilityUnits
from ALMAFE.common.GitVersion import gitVersion, gitBranch
from Measure.Stability.StabilityActions import StabilityActions
from Measure.Stability.CalcDataInterface import StabilityRecord
from Measure.Stability.CalcDataAmplitudeStability import CalcDataAmplitudeStability
from Measure.Stability.CalcDataPhaseStability import CalcDataPhaseStability
from Measure.Stability.schemas import TimeSeriesInfo
from DebugOptions import *

settingsContainer = app_CTS.measProcedure.Stability.settingsContainer
dataDisplay = app_Common.measProcedure.DataDisplay.dataDisplay
measurementStatus = app_Common.measProcedure.MeasurementStatus.measurementStatus()
receiver = hardware.FEMC.cartAssembly
ifSystem = hardware.IFSystem.ifSystem
pdPNA = PDPNA(hardware.BeamScanner.pna)
pdVoltMeter = PDVoltMeter(hardware.Stability.voltMeter)

actor = StabilityActions(
    dutType = DUT_Type.Band6_Cartridge,
    loReference = hardware.ReferenceSources.loReference,
    receiver = receiver,
    ifSystem = ifSystem,
    tempMonitor = hardware.NoiseTemperature.temperatureMonitor,
    chopper = hardware.NoiseTemperature.chopper,
    rfSrcDevice = hardware.FEMC.rfSrcDevice,    
    measurementStatus = measurementStatus,
    dataDisplay = app_Common.measProcedure.DataDisplay.dataDisplay,
    settings = settingsContainer
)

def traceToStabilityRecords(
        trace: dict, 
        fkCartTest: int,
        tsId: int,
        freqLO: float, 
        freqRF: float | None, 
        pol: int, 
        sb: str 
    ) -> list[StabilityRecord]:
    return [
        StabilityRecord(
            fkCartTest = fkCartTest,
            fkRawData = tsId,
            timeStamp = datetime.now(),
            freqLO = freqLO,
            freqCarrier = freqRF if freqRF is not None else 0,
            pol = pol,
            sideband = 0 if sb.upper() == 'LSB' else 1,
            time = x,
            allan = y,
            errorBar = e
        )
    for x, y, e in zip(trace['x'], trace['y'], trace['yError'])]
