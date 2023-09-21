
from Measure.Stability.AmplitudeStablility import AmplitudeStability
from Measure.Stability.schemas import Settings
from hardware.FEMC import cartAssembly, rfSrcDevice
from hardware.ReferenceSources import loReference
from hardware.WarmIFPlate import warmIFPlate
from hardware.NoiseTemperature import temperatureMonitor, powerMeter, chopper
from hardware.Stability import voltMeter
from .MeasurementStatus import measurementStatus
from DebugOptions import *

amplitudeStablilty = AmplitudeStability(
    loReference = loReference,
    cartAssembly = cartAssembly,
    warmIFPlate = warmIFPlate,
    voltMeter = voltMeter,
    tempMonitor = temperatureMonitor,
    measurementStatus = measurementStatus
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