from hardware.ReferenceSources import loReference, rfReference
from hardware.FEMC import cartAssembly, rfSrcDevice
from hardware.WarmIFPlate import warmIFPlate
from hardware.NoiseTemperature import powerMeter, powerSupply, temperatureMonitor, chopper
from app.measProcedure.MeasurementStatus import measurementStatus
from DebugOptions import *
from Measure.NoiseTemperature.Main import NoiseTempMain
from Measure.NoiseTemperature.YFactor import YFactor
from Measure.NoiseTemperature.schemas import CommonSettings, WarmIFSettings, NoiseTempSettings

noiseTemperature = NoiseTempMain(
    loReference = loReference, 
    rfReference = rfReference,
    cartAssembly = cartAssembly,
    rfSrcDevice = rfSrcDevice,
    warmIFPlate = warmIFPlate, 
    powerMeter = powerMeter,
    powerSupply = powerSupply,
    temperatureMonitor = temperatureMonitor,
    chopper = chopper,
    measurementStatus = measurementStatus
)

noiseTemperature.commonSettings = CommonSettings()
noiseTemperature.warmIFSettings = WarmIFSettings()
noiseTemperature.noiseTempSetings = NoiseTempSettings()
noiseTemperature.loWgIntegritySettings = NoiseTempSettings(loStep = 0.1, ifStart = 6.0, ifStop = 6.0)

yFactor = YFactor(
    powerMeter,
    powerSupply,
    chopper,
    noiseTemperature.commonSettings
)
