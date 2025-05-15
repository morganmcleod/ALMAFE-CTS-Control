import logging
from .Imports.NoiseTemperature import *

def main():
    try:
        # get the MixerTests record for this test:
        test_record: MixerTest = measurementStatus.getMeasuring()

        # read the mixer configuration:
        DB = MixerConfigs(driver = CTSDB())
        mixer_configs: list[MixerConfig] = DB.read(test_record.configId)
        if not mixer_configs:
            logger.error(f"Could not load mixer configuration {test_record.configId}")
            return
        else:
            # first/only item in the list:        
            mixer_config: MixerConfig = mixer_configs[0]
            mixer_keys: MixerKeys = DB.readKeys(mixer_config.key)

        # tell the MixerAssembly to load its configuration:
        receiver.setConfig(test_record.configId)

        # initiate the test:
        coldLoad.startFill()
        testSteps = settingsContainer.testSteps
        noiseTempSettings = settingsContainer.noiseTempSettings
        # only measure "pol0" on MTS:
        noiseTempSettings.polarization = SelectPolarization.POL0.value
        actor.start(noiseTempSettings)

        # measure warm IF noise:
        if testSteps.warmIF:
            records = actor.measureIFSysNoise(test_record.key, settingsContainer.warmIFSettings)
            DB = WarmIFNoiseData(driver = CTSDB())
            DB.create(records)

        # measure noise temperature and/or image rejection:
        if testSteps.noiseTemp or testSteps.imageReject:
            DB = NoiseTempRawData(driver = CTSDB())

            # for noise temp, can we use swep mode?
            sweepNoiseTemp = powerDetect.detect_mode == DetectMode.SPEC_AN

            # loop on LO frequencies:
            for freqLO in makeSteps(noiseTempSettings.loStart, noiseTempSettings.loStop, noiseTempSettings.loStep):
                if measurementStatus.stopNow():
                    actor.stop()
                    break

                records = None

                success, msg = actor.setLO(freqLO)
                if not success:
                    logger.error(msg)
                elif msg:
                    logger.info(msg)

                # measure noise temperature in sweep mode:
                if sweepNoiseTemp:
                    if testSteps.noiseTemp:
                        actor.checkColdLoad()
                        records = actor.measureNoiseTemp(test_record.key, freqLO, recordsIn = records)
                
                if not sweepNoiseTemp or (testSteps.imageReject and receiver.is2SB()):
                    # measure noise temp and/or image rejection in IF-stepping mode:
                    for freqIF in makeSteps(noiseTempSettings.ifStart, noiseTempSettings.ifStop, noiseTempSettings.ifStep):
                        if measurementStatus.stopNow():
                            actor.stop()
                            break
                        actor.setIF(freqIF)
                        if testSteps.noiseTemp and not sweepNoiseTemp:
                            records = actor.measureNoiseTemp(test_record.key, freqLO, freqIF, recordsIn = records)
                        if measurementStatus.stopNow():
                            actor.stop()
                            break

                        # measure image rejection:
                        if testSteps.imageReject:
                            records = actor.measureImageReject(test_record.key, freqLO, freqIF, recordsIn = records)

                # write all records for this LO to the database:
                if records is not None:
                    DB.create(list(records.values()))

    finally:
        # these will execute even if an exception is thrown above
        coldLoad.stopFill()
        actor.finish()
