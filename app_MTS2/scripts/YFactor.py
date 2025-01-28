from .Imports.NoiseTemperature import *

def main():
    settings = settingsContainer.yFactorSettings

    if settings.detectMode not in (DetectMode.DEFAULT, DetectMode.SPEC_AN):
        measurementStatus.setStatusMessage(f"Power detect mode {settings.detectMode.value} not supported on MTS-2", error = True)
        return

    ifSystem.input_select = settings.inputSelect
    ifSystem.attenuation = settings.attenuation
    
    actor.start(settingsContainer.noiseTempSettings)
    
    actor.measureYFactor(settings)

    actor.stop()
