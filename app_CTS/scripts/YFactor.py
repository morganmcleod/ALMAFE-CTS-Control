from .Imports.NoiseTemperature import *
from INSTR.SpectrumAnalyzer.schemas import SpectrumAnalyzerSettings

def main():
    settings = settingsContainer.yFactorSettings
    # settingsContainer.ntSpecAnSettings = SpectrumAnalyzerSettings(attenuation = 2, enableInternalPreamp = True)

    ifSystem.input_select = settings.inputSelect
    ifSystem.attenuation = settings.attenuation
    
    # if user has overridden the default detectMode or if the default is METER:
    if settings.detectMode == DetectMode.METER or (settings.detectMode == DetectMode.DEFAULT and powerDetect.detect_mode == DetectMode.METER):
        # set the YIG filter
        ifSystem.frequency = settings.ifStart
        ifSystem.bandwidth = 0
        actor.powerDetect = pdPowerMeter
    # if user has overridden default detect mode or if the default is SPEC_AN:
    elif settings.detectMode == DetectMode.SPEC_AN or (settings.detectMode == DetectMode.DEFAULT and powerDetect.detect_mode == DetectMode.SPEC_AN):
        # set the analyzer center and span:    
        ifSystem.frequency = (settings.ifStop - settings.ifStart) / 2 + settings.ifStart
        ifSystem.bandwidth = settings.ifStop - settings.ifStart
        actor.powerDetect = powerDetect
    
    actor.measureYFactor(settings)
