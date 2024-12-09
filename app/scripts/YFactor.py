from .Imports.NoiseTemperature import *
from INSTR.SpectrumAnalyzer.schemas import SpectrumAnalyzerSettings

def main():
    actor.ntSpecAnSettings = SpectrumAnalyzerSettings(attenuation = 2, enableInternalPreamp = True)
    actor.measureYFactor(settingsContainer.yFactorSettings)