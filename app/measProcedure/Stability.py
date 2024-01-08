
from Measure.Stability.MeasureStablility import MeasureStability
from Measure.Stability.schemas import Settings
from Measure.Stability.SampleVoltMeter import SampleVoltMeter
from Measure.Stability.SamplePNA import SamplePNA
from Measure.Stability.CalcDataAmplitudeStability import CalcDataAmplitudeStability
from Measure.Stability.CalcDataPhaseStability import CalcDataPhaseStability
from hardware.FEMC import cartAssembly, rfSrcDevice
from hardware.ReferenceSources import loReference
from hardware.WarmIFPlate import warmIFPlate
from hardware.NoiseTemperature import temperatureMonitor, powerMeter, chopper
from hardware.Stability import voltMeter
from hardware.BeamScanner import pna
from app.database.CTSDB import CTSDB
from app.measProcedure.MeasurementStatus import measurementStatus
from DebugOptions import *

sampleVoltMeter = SampleVoltMeter(voltMeter)
calcDataAmplitudeStability = CalcDataAmplitudeStability(driver = CTSDB())

amplitudeStablilty = MeasureStability(
    loReference = loReference,
    cartAssembly = cartAssembly,
    warmIFPlate = warmIFPlate,
    sampler = sampleVoltMeter,
    tempMonitor = temperatureMonitor,
    rfSrcDevice = None,
    measurementStatus = measurementStatus,
    calcDataInterface = calcDataAmplitudeStability
)

amplitudeStablilty.settings = Settings()

if TESTING:
    amplitudeStablilty.settings = Settings(
        delayAfterLock = 0,
        measureDuration = 2,
        measurePol0 = True,
        measurePol1 = False,
        measureUSB = True,
        measureLSB = False,
        loStart = 221.0,
        loStop = 221.0,
        loStep = 0
    )

samplePNA = SamplePNA(pna)
calcDataPhaseStability = CalcDataPhaseStability(driver = CTSDB())

phaseStability = MeasureStability(
    loReference = loReference,
    cartAssembly = cartAssembly,
    warmIFPlate = warmIFPlate,
    sampler = samplePNA,
    tempMonitor = temperatureMonitor,
    rfSrcDevice = rfSrcDevice,
    measurementStatus = measurementStatus,
    calcDataInterface = calcDataPhaseStability
)

phaseStability.settings = Settings(sampleRate = 5, attenuateIF = 22)

if TESTING:
    phaseStability.settings = Settings(
        sampleRate = 5,
        attenuateIF = 22,
        delayAfterLock = 0,
        measureDuration = 2,
        measurePol0 = True,
        measurePol1 = False,
        measureUSB = True,
        measureLSB = False,
        loStart = 221.0,
        loStop = 221.0,
        loStep = 0
    )
