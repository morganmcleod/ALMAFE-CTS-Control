
from hardware.FEMC import cartAssembly, rfSrcDevice
from hardware.ReferenceSources import loReference
from hardware.NoiseTemperature import temperatureMonitor
from hardware.Stability import voltMeter
from hardware.BeamScanner import pna
from hardware.IFSystem import ifSystem
from Control.PowerDetect.PDPNA import PDPNA
from Control.PowerDetect.PDVoltMeter import PDVoltMeter
from app.measProcedure.MeasurementStatus import measurementStatus
from Measure.Stability.MeasureStablility import MeasureStability
from Measure.Stability.CalcDataAmplitudeStability import CalcDataAmplitudeStability
from Measure.Stability.CalcDataPhaseStability import CalcDataPhaseStability
from app.database.CTSDB import CTSDB
from DebugOptions import *


pdVoltMeter = PDVoltMeter(voltMeter)
calcDataAmplitudeStability = CalcDataAmplitudeStability(driver = CTSDB())

amplitudeStablilty = MeasureStability(
    mode = 'AMPLITUDE',
    loReference = loReference,
    cartAssembly = cartAssembly,
    ifSystem = ifSystem,
    powerDetect = pdVoltMeter,
    tempMonitor = temperatureMonitor,
    rfSrcDevice = None,
    measurementStatus = measurementStatus,
    calcDataInterface = calcDataAmplitudeStability
)

pdPNA = PDPNA(pna)
calcDataPhaseStability = CalcDataPhaseStability(driver = CTSDB())

phaseStability = MeasureStability(
    mode = 'PHASE',
    loReference = loReference,
    cartAssembly = cartAssembly,
    ifSystem = ifSystem,
    powerDetect = pdPNA,
    tempMonitor = temperatureMonitor,
    rfSrcDevice = rfSrcDevice,
    measurementStatus = measurementStatus,
    calcDataInterface = calcDataPhaseStability
)
