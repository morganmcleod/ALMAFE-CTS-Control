from .NTCommon import *

def y_factor():
    global ntSpecAnSettings, yFactorSettings
    ifSystem = IFSystem(externalSwitch, spectrumAnalyzer)
    powerDetect = PDSpecAn(spectrumAnalyzer)

    actor = NoiseTempActions(
        loReference,
        rfReference,
        receiver,
        rfSrcDevice,
        ifSystem,
        powerDetect, 
        temperatureMonitor,
        powerSupply, 
        coldLoad,
        chopper, 
        measurementStatus,
        dataDisplay,
        DUT_Type.Band6_Cartridge,
        settings
    )
    actor.ntSpecAnSettings = SpectrumAnalyzerSettings(attenuation = 2, enableInternalPreamp = True)
    actor.measureYFactor(settings.yFactorSettings)