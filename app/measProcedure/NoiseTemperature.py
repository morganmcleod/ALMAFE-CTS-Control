from hardware.ReferenceSources import loReference, rfReference
from hardware.FEMC import cartAssembly, rfSrcDevice
from hardware.WarmIFPlate import warmIFPlate
from hardware.NoiseTemperature import powerMeter, powerSupply, temperatureMonitor, coldLoad, chopper
from app.measProcedure.MeasurementStatus import measurementStatus
from DebugOptions import *
from Measure.NoiseTemperature.Main import NoiseTempMain
from Measure.NoiseTemperature.YFactor import YFactor

noiseTemperature = NoiseTempMain(
    loReference = loReference, 
    rfReference = rfReference,
    cartAssembly = cartAssembly,
    rfSrcDevice = rfSrcDevice,
    warmIFPlate = warmIFPlate, 
    powerMeter = powerMeter,
    powerSupply = powerSupply,
    temperatureMonitor = temperatureMonitor,
    coldLoadController = coldLoad,
    chopper = chopper,
    measurementStatus = measurementStatus
)

yFactor = YFactor(
    warmIFPlate,
    powerMeter,
    temperatureMonitor,
    chopper,
    noiseTemperature.commonSettings,
    measurementStatus
)
