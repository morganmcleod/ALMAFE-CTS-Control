import logging
from .Imports.MixerTests import *

def main():
    logger = logging.getLogger("ALMAFE-CTS-Control")
    settings = settingsContainer.magnetOptSettings
    
    cart_test = measurementStatus.getMeasuring()
    receiver.setConfig(cart_test.configId)

    actor.start(settingsContainer)

    actor.magnetOptimize(settings, resultsTarget = dataDisplay.magnetOptResults)

    actor.stop()
