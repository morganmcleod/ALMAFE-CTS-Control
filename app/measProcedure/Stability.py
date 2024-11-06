
import hardware.FEMC
import hardware.ReferenceSources 
import hardware.NoiseTemperature
import hardware.Stability
import hardware.BeamScanner
import hardware.IFSystem
import app.measProcedure.MeasurementStatus
import measProcedure.DataDisplay
from Control.PowerDetect.PDPNA import PDPNA
from Control.PowerDetect.PDVoltMeter import PDVoltMeter
from Measure.Stability.MeasureStablility import MeasureStability
from Measure.Stability.CalcDataAmplitudeStability import CalcDataAmplitudeStability
from Measure.Stability.CalcDataPhaseStability import CalcDataPhaseStability
from Measure.Stability.SettingsContainer import SettingsContainer
from app.database.CTSDB import CTSDB
from DebugOptions import *

settingsContainer = SettingsContainer()

pdVoltMeter = PDVoltMeter(hardware.Stability.voltMeter)
calcDataAmplitudeStability = CalcDataAmplitudeStability(driver = CTSDB())

amplitudeStablilty = MeasureStability(
    mode = 'AMPLITUDE',
    loReference = hardware.ReferenceSources.loReference,
    cartAssembly = hardware.FEMC.cartAssembly,
    ifSystem = hardware.IFSystem.ifSystem,
    powerDetect = pdVoltMeter,
    tempMonitor = hardware.NoiseTemperature.temperatureMonitor,
    rfSrcDevice = None,
    measurementStatus = app.measProcedure.MeasurementStatus.measurementStatus(),
    calcDataInterface = calcDataAmplitudeStability,
    dataDisplay = measProcedure.DataDisplay.dataDisplay,
    settingsContainer = settingsContainer
)

pdPNA = PDPNA(hardware.BeamScanner.pna)
calcDataPhaseStability = CalcDataPhaseStability(driver = CTSDB())

phaseStability = MeasureStability(
    mode = 'PHASE',
    loReference = hardware.ReferenceSources.loReference,
    cartAssembly = hardware.FEMC.cartAssembly,
    ifSystem = hardware.IFSystem.ifSystem,
    powerDetect = pdPNA,
    tempMonitor = hardware.NoiseTemperature.temperatureMonitor,
    rfSrcDevice = hardware.FEMC.rfSrcDevice,
    measurementStatus = app.measProcedure.MeasurementStatus.measurementStatus(),
    calcDataInterface = calcDataPhaseStability,
    dataDisplay = measProcedure.DataDisplay.dataDisplay,
    settingsContainer = settingsContainer
)
