import logging
from .Imports.MixerTests import *

def main():
    logger = logging.getLogger("ALMAFE-CTS-Control")
    settings = settingsContainer.magnetOptSettings
    
    testRec = measurementStatus.getMeasuring()
    receiver.setConfig(testRec.configId)

    actor.start(settingsContainer)

    actor.magnetOptimize(settings, dataDisplay.magnetOptResults)

    actor.stop()
