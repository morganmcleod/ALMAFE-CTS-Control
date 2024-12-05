import logging
from .Imports.NoiseTemperature import *

def main():
    logger = logging.getLogger("ALMAFE-CTS-Control")
    actor.ntSpecAnSettings = settingsContainer.ntSpecAnSettings
    
    cart_test = measurementStatus.getMeasuring()
    receiver.setCartConfig(cart_test.configId)

    coldLoad.startFill()

    actor.start(settingsContainer.noiseTempSettings)

    if settingsContainer.testSteps.warmIF:
        warmIFSettings = actor.loadSettingsWarmIF()
        records = actor.measureIFSysNoise(cart_test.key, warmIFSettings)
        DB = WarmIFNoiseData(driver = CTSDB())
        DB.create(records)

    DB = NoiseTempRawData(driver = CTSDB())
    polSel = SelectPolarization(settingsContainer.biasOptSettings.polarization)

    for freqLO in makeSteps(settingsContainer.noiseTempSettings.loStart, settingsContainer.noiseTempSettings.loStop, settingsContainer.noiseTempSettings.loStep):
        if actor.finished or measurementStatus.stopNow():
            break
        actor.checkColdLoad()
        actor.setLO(freqLO, setBias = False)

        stopNow = False
        for pol in (0, 1):
            if polSel.testPol(pol):

                noiseTemps = {}
                optimumNoiseTemp = 9e9
                optimumRecords = None

                VJ = settingsContainer.biasOptSettings.vjMin
                header = "Ij:"
                first = True
                while VJ <= settingsContainer.biasOptSettings.vjMax and not stopNow:
                    row = f"Vj={VJ}"
                    receiver.ccaDevice.setSIS(pol, 1, -VJ)
                    receiver.ccaDevice.setSIS(pol, 1, VJ)

                    IJ = settingsContainer.biasOptSettings.ijMin
                    while IJ <= settingsContainer.biasOptSettings.ijMax and not stopNow:
                        row += f"Ij={IJ}"
                        receiver.autoLOPower(pol0 = pol == 0, pol1 = pol == 1, targetIJ = IJ)
                        records = actor.measureNoiseTemp(cart_test.key, freqLO, receiver.isLocked(), freqIF = 0)
                        meanNoiseTemp = actor.calcMeanNoiseTemp(records)
                        noiseTemps[(VJ, IJ)] = meanNoiseTemp
                        if first:
                            header += "\t{IJ}"
                        row += f"\{meanNoiseTemp:.2f}"
                        if meanNoiseTemp < optimumNoiseTemp:
                            optimumNoiseTemp = meanNoiseTemp
                            optimumRecords = records
                        
                        IJ += settingsContainer.biasOptSettings.ijStep
                        stopNow = actor.finished or measurementStatus.stopNow()
                    if first:
                        logger.info(header)
                        first = False
                    logger.info(row)
                    VJ += settingsContainer.biasOptSettings.vjStep
                
                DB.create(list(optimumRecords.values))

    coldLoad.stopFill()    
    actor.stop()
