import logging
from .Imports.NoiseTemperature import *

def main():
    logger = logging.getLogger("ALMAFE-CTS-Control")
    
    next_pos = beamScanMotorController.getPosition()
    next_pos.pol = -58.5
    beamScanMotorController.setNextPos(next_pos)
    beamScanMotorController.startMove()

    cart_test = measurementStatus.getMeasuring()
    receiver.setConfig(cart_test.configId)

    coldLoad.startFill()
    noiseTempSettings = settingsContainer.loWgIntegritySettings if settingsContainer.testSteps.loWGIntegrity else settingsContainer.noiseTempSettings
    actor.start(noiseTempSettings)

    if settingsContainer.testSteps.warmIF:
        records = actor.measureIFSysNoise(cart_test.key, settingsContainer.warmIFSettings)
        DB = WarmIFNoiseData(driver = CTSDB())
        DB.create(records)

    doIFStepping = settingsContainer.testSteps.imageReject or powerDetect.detect_mode == DetectMode.METER

    if settingsContainer.testSteps.noiseTemp or settingsContainer.testSteps.loWGIntegrity or settingsContainer.testSteps.imageReject:
        DB = NoiseTempRawData(driver = CTSDB())
        for freqLO in makeSteps(noiseTempSettings.loStart, noiseTempSettings.loStop, noiseTempSettings.loStep):
            if measurementStatus.stopNow():
                actor.stop()
                break
            
            coldLoad.startFill()
            actor.setLO(freqLO, setBias = True)

            records = None
            if not doIFStepping:
                if settingsContainer.testSteps.noiseTemp or settingsContainer.testSteps.loWGIntegrity:
                    actor.checkColdLoad()
                    records = actor.measureNoiseTemp(cart_test.key, freqLO, receiver.isLocked(), freqIF = 0, recordsIn = records)
            else:
                for freqIF in makeSteps(noiseTempSettings.ifStart, noiseTempSettings.ifStop, noiseTempSettings.ifStep):
                    if measurementStatus.stopNow():
                        actor.stop()
                        break
                    actor.setIF(freqIF)
                    if settingsContainer.testSteps.noiseTemp or settingsContainer.testSteps.loWGIntegrity:
                        records = actor.measureNoiseTemp(cart_test.key, freqLO, receiver.isLocked(), freqIF, recordsIn = records)
                    if measurementStatus.stopNow():
                        actor.stop()
                        break
                    if settingsContainer.testSteps.imageReject:
                        records = actor.measureImageReject(cart_test.key, freqLO, receiver.isLocked(), freqIF, recordsIn = records)

            if records is not None:
                DB.create(list(records.values()))

    coldLoad.stopFill()    
    actor.finish()
