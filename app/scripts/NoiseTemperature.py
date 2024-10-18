import logging
from .Imports.NoiseTemperature import *

def main():
    logger = logging.getLogger("ALMAFE-CTS-Control")
    settings = settingsContainer.commonSettings
    
    next_pos = beamScanMotorController.getPosition()
    next_pos.pol = -58.5
    beamScanMotorController.setNextPos(next_pos)
    beamScanMotorController.startMove()

    cart_test = measurementStatus.getMeasuring()
    receiver.setConfig(cart_test.configId)

    coldLoad.startFill()
    noiseTempSettings = settings.loWgIntegritySettings if settings.testSteps.loWGIntegrity else settings.noiseTempSettings
    actor.start(noiseTempSettings)

    if settings.testSteps.warmIF:
        records = actor.measureIFSysNoise(cart_test.key, settings.warmIFSettings)
        DB = WarmIFNoiseData(driver = CTSDB())
        DB.create(records)

    if settings.testSteps.noiseTemp or settings.testSteps.loWGIntegrity or settings.testSteps.imageReject:
        DB = NoiseTempRawData(driver = CTSDB())
        for freqLO in makeSteps(noiseTempSettings.loStart, noiseTempSettings.loStop, noiseTempSettings.loStep):
            if measurementStatus.stopNow():
                actor.stop()
                break
            
            coldLoad.startFill()
            actor.setLO(freqLO, setBias = True)

            records = None
            if settings.testSteps.noiseTemp or settings.testSteps.loWGIntegrity:
                actor.checkColdLoad()
                records = actor.measureNoiseTemp(cart_test.key, freqLO, receiver.isLocked(), freqIF = 0)
            
            if settings.testSteps.imageReject:
                for freqIF in makeSteps(noiseTempSettings.ifStart, noiseTempSettings.ifStop, noiseTempSettings.ifStep):
                    if measurementStatus.stopNow():
                        actor.stop()
                        break
                    actor.setIF(freqIF)
                    records = actor.measureImageReject(cart_test.key, freqLO, receiver.isLocked(), freqIF, recordsIn = records)

            if records is not None:
                DB.create(list(records.values()))

    coldLoad.stopFill()    
    actor.finish()
