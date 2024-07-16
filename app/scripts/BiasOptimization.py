import logging
from .NTCommon import *

def bias_optimization():
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
        DUT_Type.Band6_Cartridge
    )
    actor.ntSpecAnSettings = settings.ntSpecAnSettings
    
    cart_test = measurementStatus.getMeasuring()
    receiver.setConfig(cart_test.configId)

    coldLoad.startFill()

    actor.start(settings.commonSettings, settings.noiseTempSettings)

    if settings.testSteps.warmIF:
        warmIFSettings = actor.loadSettingsWarmIF()
        records = actor.measureIFSysNoise(cart_test.key, warmIFSettings)
        DB = WarmIFNoiseData(driver = CTSDB())
        DB.create(records)

    DB = NoiseTempRawData(driver = CTSDB())
    polSel = SelectPolarization(settings.biasOptSettings.polarization)

    for freqLO in makeSteps(settings.noiseTempSettings.loStart, settings.noiseTempSettings.loStop, settings.noiseTempSettings.loStep):
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

                VJ = settings.biasOptSettings.vjMin
                header = "Ij:"
                first = True
                while VJ <= settings.biasOptSettings.vjMax and not stopNow:
                    row = f"Vj={VJ}"
                    receiver.ccaDevice.setSIS(pol, 1, -VJ)
                    receiver.ccaDevice.setSIS(pol, 1, VJ)

                    IJ = settings.biasOptSettings.ijMin
                    while IJ <= settings.biasOptSettings.ijMax and not stopNow:
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
                        
                        IJ += settings.biasOptSettings.ijStep
                        stopNow = actor.finished or measurementStatus.stopNow()
                    if first:
                        logger.info(header)
                        first = False
                    logger.info(row)
                    VJ += settings.biasOptSettings.vjStep
                
                DB.create(list(optimumRecords.values))

    coldLoad.stopFill()    
    actor.stop()
