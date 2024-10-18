import logging
from .Imports.MixerTests import *

def main():
    logger = logging.getLogger("ALMAFE-CTS-Control")
    settings = settingsContainer.defluxSettings
    
    cart_test = measurementStatus.getMeasuring()
    receiver.setConfig(cart_test.configId)

    actor.start(settingsContainer)

    actor.mixersDeflux(settings, resultsTarget = dataDisplay.defluxResults)

    actor.stop()
