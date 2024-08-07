from .NTCommon import *
from INSTR.SpectrumAnalyzer.schemas import SpectrumAnalyzerSettings

def y_factor():
    actor.ntSpecAnSettings = SpectrumAnalyzerSettings(attenuation = 2, enableInternalPreamp = True)
    actor.measureYFactor(settings.yFactorSettings)