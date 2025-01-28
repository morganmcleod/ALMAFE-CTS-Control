from .Imports.MixerTests import *

def prepare_data(
        testRec: MixerTest, 
        sis: SelectSIS, 
        freqLO: float, 
        pumpPwr: float,
        iMag: float, 
        points: list[AMB_IVCurvePoint]
    ) -> list[DB_IVCurvePoint]:
        """Convert a list of AMB_IVCurvePoint into a list of DB_IVCurvePoint for insertion into database"""
        return [DB_IVCurvePoint(
            fkMxrPreampAssys = testRec.configId,
            fkMixerTest = testRec.key,
            FreqLO = freqLO,
            MixerChip = "1L" if sis == SelectSIS.SIS1 else "2R",
            Imag = iMag,
            Vj = point.vjRead,
            Ij = point.ijRead,
            IFPower = point.ifPower,
            isPCold = point.isPCold,
            PumpPwr = pumpPwr
    ) for point in points if point.is_valid()]

def main():
    settings = settingsContainer.ivCurveSettings
    
    testRec = measurementStatus.getMeasuring()
    receiver.setConfig(testRec.configId)

    DB = IVCurves(driver = CTSDB())

    if not settings.enable01 and not settings.enable02:
        measurementStatus.setStatusMessage("Neither mixer was selected.", error = True)
        return

    actor.start(settingsContainer)

    if settings.measurePHot:
        if settings.ifStart == settings.ifStop:
            ifSystem.frequency = settings.ifStart
            ifSystem.bandwidth = 0.1
        else:
            span = settings.ifStop - settings.ifStart
            ifSystem.frequency = settings.ifStart + span / 2
            ifSystem.bandwidth = span
        ifSystem.output_select = OutputSelect.POWER_DETECT

    # set the magnet bias:
    receiver.setBias(0, magnetOnly = True)

    if settings.unPumped:
        dataDisplay.ivCurveResults.reset()
        receiver.setPAOutput(SelectPolarization.BOTH, 0)

        results = actor.measureIVCurves(settings, dataDisplay.ivCurveResults)
        mp1, _ = receiver.getTargetMixersBias()
        
        if settings.enable01 and settings.saveResults:
            to_insert = prepare_data(testRec, SelectSIS.SIS1, 0, 0, mp1.IMAG if mp1 else 0, results.curves[0].points)
            DB.create(to_insert)
    
        if settings.enable02 and settings.saveResults:
            to_insert = prepare_data(testRec, SelectSIS.SIS2, 0, 0, mp1.IMAG if mp1 else 0, results.curves[1].points)
            DB.create(to_insert)

    if settings.loPumped:
        for freqLO in makeSteps(settings.loStart, settings.loStop, settings.loStep):
            if measurementStatus.stopNow():
                actor.stop()
                break
            
            dataDisplay.ivCurveResults.reset()
            actor.setLO(freqLO, settings.lockLO, loPumped = True)
            results = actor.measureIVCurves(settings, dataDisplay.ivCurveResults, ifPowerImpl)
            mp1, _ = receiver.getTargetMixersBias()
            pumpPwr = receiver.getPAOutput(SelectPolarization.POL0)
        
            if settings.enable01 and settings.saveResults:
                to_insert = prepare_data(testRec, SelectSIS.SIS1, freqLO, pumpPwr, mp1.IMAG, results.curves[0].points)
                DB.create(to_insert)
        
            if settings.enable02 and settings.saveResults:
                to_insert = prepare_data(testRec, SelectSIS.SIS2, freqLO, pumpPwr, mp1.IMAG, results.curves[1].points)
                DB.create(to_insert)

    actor.finish()
