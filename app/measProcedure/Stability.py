
from hardware.FEMC import cartAssembly, rfSrcDevice
from hardware.ReferenceSources import loReference
from hardware.WarmIFPlate import warmIFPlate
from hardware.NoiseTemperature import temperatureMonitor, powerMeter, chopper
from hardware.Stability import voltMeter
from hardware.BeamScanner import pna
from app.measProcedure.MeasurementStatus import measurementStatus
from Measure.Stability.MeasureStablility import MeasureStability
from Measure.Stability.schemas import Settings
from Measure.Stability.SampleVoltMeter import SampleVoltMeter
from Measure.Stability.SamplePNA import SamplePNA
from Measure.Stability.CalcDataAmplitudeStability import CalcDataAmplitudeStability
from Measure.Stability.CalcDataPhaseStability import CalcDataPhaseStability
from app.database.CTSDB import CTSDB
from DebugOptions import *

sampleVoltMeter = SampleVoltMeter(voltMeter)
calcDataAmplitudeStability = CalcDataAmplitudeStability(driver = CTSDB())

amplitudeStablilty = MeasureStability(
    mode = 'AMPLITUDE',
    loReference = loReference,
    cartAssembly = cartAssembly,
    warmIFPlate = warmIFPlate,
    sampler = sampleVoltMeter,
    tempMonitor = temperatureMonitor,
    rfSrcDevice = None,
    measurementStatus = measurementStatus,
    calcDataInterface = calcDataAmplitudeStability
)

samplePNA = SamplePNA(pna)
calcDataPhaseStability = CalcDataPhaseStability(driver = CTSDB())

phaseStability = MeasureStability(
    mode = 'PHASE',
    loReference = loReference,
    cartAssembly = cartAssembly,
    warmIFPlate = warmIFPlate,
    sampler = samplePNA,
    tempMonitor = temperatureMonitor,
    rfSrcDevice = rfSrcDevice,
    measurementStatus = measurementStatus,
    calcDataInterface = calcDataPhaseStability
)
