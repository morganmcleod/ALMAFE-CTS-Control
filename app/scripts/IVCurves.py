import logging
from .Imports.MixerTests import *

def main():
    logger = logging.getLogger("ALMAFE-CTS-Control")
    settings = settingsContainer.ivCurveSettings
    
    cart_test = measurementStatus.getMeasuring()
    serialNum = receiver.settings.serialNum
    receiver.setConfig(cart_test.configId)

    actor.start(settingsContainer)

    if settings.measureIFPower:
        ifSystem.frequency = 6.0
        ifSystem.attenuation = 20.0
        ifSystem.output_select = OutputSelect.POWER_DETECT

    if settings.loPumped:
        for freqLO in makeSteps(settings.loStart, settings.loStop, settings.loStep):
            if measurementStatus.stopNow():
                actor.stop()
                break
            
            dataDisplay.ivCurveResults.reset()
            actor.setLO(freqLO, settings.lockLO, settings.loPumped)            
            actor.measureIVCurve(settings, ifPowerImpl, resultsTarget = dataDisplay.ivCurveResults)
    
    else:
        # assume the receiver is already biased.  Just do the measurement:
        dataDisplay.ivCurveResults.reset()
        receiver.setRecevierBias(FreqLO = 0, magnetOnly = True)
        actor.measureIVCurve(settings, ifPowerImpl, resultsTarget = dataDisplay.ivCurveResults)

    actor.finish()
