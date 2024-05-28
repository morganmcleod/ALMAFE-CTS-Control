from hardware.ReferenceSources import loReference, rfReference
from hardware.FEMC import cartAssembly, rfSrcDevice
from hardware.WarmIFPlate import warmIFPlate, externalSwitch
from hardware.NoiseTemperature import powerMeter, powerSupply, temperatureMonitor, coldLoad, chopper, spectrumAnalyzer
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
    spectrumAnalyzer = spectrumAnalyzer,
    powerSupply = powerSupply,
    temperatureMonitor = temperatureMonitor,
    coldLoadController = coldLoad,
    chopper = chopper,
    measurementStatus = measurementStatus,
    externalSwitch = externalSwitch
)

yFactor = YFactor(
    warmIFPlate,
    powerMeter,
    temperatureMonitor,
    chopper,
    noiseTemperature.commonSettings,
    measurementStatus
)
