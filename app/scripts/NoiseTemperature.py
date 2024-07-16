import logging
from .NTCommon import *

def noise_temperature():
    logger = logging.getLogger("ALMAFE-CTS-Control")
    ifSystem = IFSystem(externalSwitch, spectrumAnalyzer)
    powerDetect = PDSpecAn(spectrumAnalyzer)

    actor = NoiseTempActions(
        loReference,
        rfReference,
        receiver,
        rfSrcDevice,
        ifSystem,
        powerDetect, 
        temperatureMonitor,
        powerSupply, 
        coldLoad,
        chopper, 
        measurementStatus,
        dataDisplay,
        DUT_Type.Band6_Cartridge,
        settings
    )

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
            actor.checkColdLoad()
            actor.setLO(freqLO, setBias = True)

            records = None
            if settings.testSteps.noiseTemp or settings.testSteps.loWGIntegrity:
                records = actor.measureNoiseTemp(cart_test.key, freqLO, receiver.isLocked(), freqIF = 0)

            coldLoad.stopFill()
            
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
