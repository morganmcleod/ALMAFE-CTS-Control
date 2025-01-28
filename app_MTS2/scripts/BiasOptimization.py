import os
import logging
from openpyxl import Workbook
from .Imports.NoiseTemperature import *

def main():
    MIN_VALID_NT = 5.0      # K
    MAX_VALID_NT = 300.0    # K
    IJ_TOLERANCE = 3.0      # uA

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
        biasOptSettings = settingsContainer.biasOptSettings
        noiseTempSettings = settingsContainer.noiseTempSettings
        # only measure "pol0" on MTS:
        noiseTempSettings.polarization = SelectPolarization.POL0.value
        actor.start(noiseTempSettings)

        # measure warm IF noise:
        if testSteps.warmIF:
            records = actor.measureIFSysNoise(test_record.key, settingsContainer.warmIFSettings)
            DB = WarmIFNoiseData(driver = CTSDB())
            DB.create(records)

        ifSystem.input_select = InputSelect.POL0_USB

        # spreadsheet to store all the raw data:
        wb = Workbook()
        rawDataSheet = wb.active
        rawDataSheet.title = "Raw data"
        rawDataSheet.append(NT_COLUMNS)
        wb.create_sheet("Results", 0)
        resultsSheet = wb["Results"]
        outPath = os.path.join(biasOptSettings.outputDir, f"BiasOpt_{mixer_config.serialNum}_{test_record.timeStamp.strftime('%Y-%m-%d_%H_%M_%S')}.xlsx")

        # loop on LO frequencies:
        for freqLO in makeSteps(noiseTempSettings.loStart, noiseTempSettings.loStop, noiseTempSettings.loStep):
            if measurementStatus.stopNow():
                actor.stop()
                break

            # will accumulate optimum bias settings and noise temps here:
            noiseTemps = {}

            # clear the operator display:
            dataDisplay.biasOptResults = []

            # set the LO and bias defaults:
            success, msg = actor.setLO(freqLO, setBias = False)
            if not success:
                logger.error(msg)
            elif msg:
                logger.info(msg)
            receiver.setSISbias(SelectSIS.SIS1, 0, biasOptSettings.iMag)

            # find the bias settings with the best mean noise temperature:
            bestVj = None
            bestIj = None
            bestNT = 9e9

            # loop on SIS voltage:
            VjSteps = makeSteps(biasOptSettings.vjStart, biasOptSettings.vjStop, biasOptSettings.vjStep)
            for Vj in VjSteps:
                if measurementStatus.stopNow():
                    actor.stop()
                    break

                receiver.setSISbias(SelectSIS.SIS1, -abs(Vj), biasOptSettings.iMag)
                receiver.setSISbias(SelectSIS.SIS2, abs(Vj))

                noiseTemps[Vj] = {}

                # loop on SIS current:
                IjSteps = makeSteps(biasOptSettings.ijStart, biasOptSettings.ijStop, biasOptSettings.ijStep)
                for Ij in IjSteps:
                    if measurementStatus.stopNow():
                        actor.stop()
                        break

                    actor.checkColdLoad()

                    chopper.gotoHot()
                    success, msg = receiver.autoLOPower(targetIJ = Ij, no_config = True)
                    if not success:
                        logger.error(msg)

                    # measure noise temperature in sweep mode:
                    statusMessage = f"Measure bias optimization LO={freqLO:.2f} GHz, Vj={Vj}, Ij={Ij}..."
                    records: list[NoiseTempRawDatum] = actor.measureNoiseTemp(test_record.key, freqLO, statusMessage = statusMessage)

                    # take the mean noise temperature across the IF range:
                    meanNT = actor.calcMeanNoiseTemp(records, biasOptSettings.ifOptimizeStart, biasOptSettings.ifOptimizeStop)

                    # find the best bias settings and actual bias current:
                    IjRead = round(records[(0, noiseTempSettings.ifStart)].Ij1, 2)
                    if abs(Ij - abs(IjRead)) <= IJ_TOLERANCE and MIN_VALID_NT <= meanNT <= MAX_VALID_NT and meanNT < bestNT:
                        bestNT = meanNT
                        bestVj = Vj
                        bestIj = Ij

                    # store all raw records in spreadsheet:
                    for rec in list(records.values()):
                        rawDataSheet.append(rec.getVals())
                    
                    # store meanNT, result record, and raw data for later retrieval:
                    noiseTemps[Vj][Ij] = {
                        'mean': meanNT,
                        'records': records,
                        'result' : BiasOptResult(
                            freqLO = freqLO,
                            VjSet = Vj,
                            IjSet = Ij,
                            IjRead = IjRead,
                            Trx = round(meanNT, 2)
                        )
                    }

                    # update the user display:
                    dataDisplay.biasOptResults.append(noiseTemps[Vj][Ij]['result'])

                    # write the output spreadsheet:                    
                    wb.save(outPath)

            # write the optimum bias settings:
            if bestVj is None:
                logger.error(f"scripts.BiasOptimization: failed to find best noise temperature for LO={freqLO}")
            else:
                DB = MixerParams(driver = CTSDB())
                DB.create(mixer_keys.keyChip1, [MixerParam(
                    FreqLO = freqLO,
                    VJ = -bestVj,
                    IJ = -bestIj,
                    IMAG = biasOptSettings.iMag,
                    timeStamp = test_record.timeStamp
                )])
                if mixer_keys.keyChip2:
                    DB.create(mixer_keys.keyChip2, [MixerParam(
                        FreqLO = freqLO,
                        VJ = bestVj,
                        IJ = bestIj,
                        IMAG = 0
                    )])

                # write the optimum noise temperature results:
                DB = NoiseTempRawData(driver = CTSDB())
                DB.create(list(noiseTemps[bestVj][bestIj]['records'].values()))

            # write the Trx results matrix to the output spreadsheet
            
            resultsSheet.append(["LO freq:", freqLO, "  ------------------------------"])
            resultsSheet.append(["TRx [K]", "Vj [mV]"])
            resultsSheet.append(["Ij [μA]"] + VjSteps)
            for Ij in IjSteps:
                row = [Ij]
                for Vj in VjSteps:
                    row.append(noiseTemps[Vj][Ij]['result'].Trx)
                resultsSheet.append(row)
            resultsSheet.append([""])

            # write the IjRead results to the spreadsheet:
            resultsSheet.append(["Ij1 [μA]", "Vj [mV]"])
            resultsSheet.append(["Ij [μA]"] + VjSteps)
            for Ij in IjSteps:
                row = [Ij]
                for Vj in VjSteps:
                    row.append(noiseTemps[Vj][Ij]['result'].IjRead)
                resultsSheet.append(row)
            resultsSheet.append([""])
            wb.save(outPath)

    finally:
        # these will execute even if an exception is thrown above
        coldLoad.stopFill()    
        actor.finish()
