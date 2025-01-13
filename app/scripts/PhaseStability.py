import copy
import logging
from datetime import datetime
from .Imports.Stability import *

def main():
    logger = logging.getLogger("ALMAFE-CTS-Control")
    
    # this collection will have one object per time series measured in the loop
    dataDisplay.timeSeriesList = []

    # database interfaces
    resultsDB = TestResults(driver = CTSDB())
    plotsDB = TestResultPlots(driver = CTSDB())
    calcDataDB = CalcDataPhaseStability(driver = CTSDB())
    timeSeriesAPI = TimeSeriesAPI()

    cart_test = measurementStatus.getMeasuring()
    assert(cart_test.fkTestType == TestTypeIds.PHASE_STABILITY.value)
    receiver.setCartConfig(cart_test.configId)

    # DataSources are associated with a time series and control what is shown on plots
    dataSources = {}
    dataSources[DataSource.DATA_KIND] = DataKind.PHASE.value
    dataSources[DataSource.DATA_SOURCE] = f"Test ID {cart_test.key}"
    dataSources[DataSource.CONFIG_ID] = cart_test.configId
    dataSources[DataSource.SERIALNUM] = receiver.settings.serialNum        
    dataSources[DataSource.TEST_SYSTEM] = cart_test.testSysName
    dataSources[DataSource.UNITS] = Units.DEG.value
    dataSources[DataSource.T_UNITS] = Units.KELVIN.value
    dataSources[DataSource.OPERATOR] = cart_test.operator
    dataSources[DataSource.NOTES] = cart_test.description
    dataSources[DataSource.MEAS_SW_NAME] = "ALMAFE-CTS-Control"
    branch = gitBranch()
    commit = gitVersion(branch = branch)
    dataSources[DataSource.MEAS_SW_VERSION] = branch + ":" + commit[0:7]

    # These are for the correction voltage time series plot
    dataSourcesCorrV = copy.copy(dataSources)
    dataSourcesCorrV[DataSource.DATA_KIND] = DataKind.VOLTAGE.value
    dataSourcesCorrV[DataSource.UNITS] = Units.VOLTS.value
    dataSourcesCorrV[DataSource.T_UNITS] = Units.CELCIUS.value

    # Test result holds additional metadata about the measurement and a list of plot IDs
    testResult = TestResult(
        fkCartTests = cart_test.key,
        dataStatus = DataStatus.MEASURED,
        measurementSW = dataSources[DataSource.MEAS_SW_VERSION],
        description = cart_test.description,
        plots = []
    )
    resultsDB.create(testResult)

    # set the actor to use the PNA for power detection, start the actor:
    actor.setPowerDetect(pdPNA)    
    settings = settingsContainer.phaseStability
    actor.start(settings)
    # set the IF attenuator:
    ifSystem.attenuation = settings.attenuateIF

    for freqLO in makeSteps(settings.loStart, settings.loStop, settings.loStep):
        if measurementStatus.stopNow():
            actor.stop()
            break
           
        actor.setLO(freqLO, setBias = True)
        if not receiver.isLocked():
            logger.error(f"Phase Stability: Skipping LO not locked at {freqLO} GHz")
            continue
        
        for pol in 0, 1:
            if SelectPolarization(settings.polarization).testPol(pol):

                if measurementStatus.stopNow():
                    actor.stop()
                    break

                for sb in 'LSB', 'USB':
                    if SelectSideband(settings.sideband).testSB(sb):
                        
                        if measurementStatus.stopNow():
                            actor.stop()
                            break
                        
                        # select the IF input:
                        ifSystem.set_pol_sideband(pol, sb)                        

                        # lock the RF source:
                        freqRF = freqLO - 10 if sb == 'LSB' else freqLO + 10
                        success, msg = actor.lockRF(freqRF)
                        if not success:
                            logger.error(f"Phase Stability: {msg}")
                            continue
                        
                        # auto-level the RF source to get the target output power
                        success, msg = actor.rfSourceAutoLevel(freqIF = 10)
                        if not success:
                            logger.warning(f"Phase Stability: {msg}")
                        actor.delayAfterLock()
                        
                        # set up time series to collect phase, correction voltage:
                        phaseSeries = TimeSeries(startTime = datetime.now(), dataUnits = Units.DEG)
                        rfCorrVSeries = TimeSeries(startTime = datetime.now(), dataUnits = Units.VOLTS)
                        loCorrVSeries = TimeSeries(startTime = datetime.now(), dataUnits = Units.VOLTS)

                        # measure phase, correction voltage, plus temperatures vs. time:
                        success, msg = actor.measurePhase(phaseSeries, loCorrVSeries, rfCorrVSeries)
                        if not success:
                            logger.error(f"Phase Stability: {msg}")
                            continue

                        if measurementStatus.stopNow():
                            actor.stop()
                            break
                        
                        # this stores metadata and plots associated with a time series
                        info = TimeSeriesInfo(
                            key = phaseSeries.tsId,
                            freqLO = freqLO,
                            pol = pol,
                            sideband = sb,
                            timeStamp = datetime.now(),
                            dataStatus = DataStatus.PROCESSED.name,
                            tau0Seconds = phaseSeries.tau0Seconds
                        )

                        # apply the dataSources to specify plot appearance:
                        dataSources[DataSource.LO_GHZ] = freqLO
                        dataSources[DataSource.RF_GHZ] = freqRF
                        dataSources[DataSource.SUBSYSTEM] = f"pol{pol} {sb}"                        
                        for key in dataSources.keys():
                            timeSeriesAPI.setDataSource(phaseSeries.tsId, key, dataSources[key])

                        # plot the phase time series:
                        plotBinary = actor.plotTimeSeries(phaseSeries)
                        info.timeSeriesPlot = plotsDB.create(TestResultPlot(plotBinary = plotBinary, description = f"Time series LO={freqLO} Pol{pol} {sb}"))
                        if info.timeSeriesPlot:
                            testResult.plots.append(info.timeSeriesPlot)
                
                        # plot the LO, RF correction voltage time series, with dataSources applied:
                        dataSourcesCorrV[DataSource.LO_GHZ] = freqLO
                        dataSourcesCorrV[DataSource.RF_GHZ] = freqRF
                        dataSourcesCorrV[DataSource.SUBSYSTEM] = f"pol{pol} {sb}"
                        
                        plotBinary = actor.plotTimeSeries(
                            loCorrVSeries, 
                            title = "LO PLL Correction Voltage", 
                            tempSensorLegend = "PLL Temperature",
                            dataSources = dataSourcesCorrV
                        )
                        info.loCorrVPlot = plotsDB.create(TestResultPlot(plotBinary = plotBinary, description = f"LO correction voltage LO={freqLO} Pol{pol} {sb}"))
                        if info.loCorrVPlot:
                            testResult.plots.append(info.loCorrVPlot)
                        
                        plotBinary = actor.plotTimeSeries(
                            rfCorrVSeries, 
                            title = "RF PLL Correction Voltage", 
                            tempSensorLegend = "PLL Temperature",
                            dataSources = dataSourcesCorrV
                        )
                        info.rfCorrVPlot = plotsDB.create(TestResultPlot(plotBinary = plotBinary, description = f"RF correction voltage LO={freqLO} Pol{pol} {sb}"))
                        if info.rfCorrVPlot:
                            testResult.plots.append(info.rfCorrVPlot)

                        # plot phase stabliity Allan deviation:
                        plotBinary, trace = actor.plotPhaseStability(phaseSeries)
                        info.allanPlot = plotsDB.create(TestResultPlot(plotBinary = plotBinary, description = f"Phase stability LO={freqLO} Pol{pol} {sb}"))
                        if info.allanPlot:
                            testResult.plots.append(info.allanPlot)
                        # store the Allan trace in the database:
                        if trace:
                            records = traceToStabilityRecords(
                                trace,
                                cart_test.key,
                                phaseSeries.tsId,
                                freqLO,
                                freqRF,
                                pol,
                                sb
                            )
                            calcDataDB.create(records)

                        # plot the FFT:
                        plotBinary = actor.plotSpectrum(phaseSeries)
                        info.spectrumPlot = plotsDB.create(TestResultPlot(plotBinary = plotBinary, description = f"Phase spectrum LO={freqLO} Pol{pol} {sb}"))
                        if info.spectrumPlot:
                            testResult.plots.append(info.spectrumPlot)

                        # add the TimeSeriesInfo record to the list for user display:
                        dataDisplay.timeSeriesList.append(info)

                        # update the TestResult record with the plots created so far:
                        testResult.timeStamp = datetime.now()
                        testResult = resultsDB.createOrUpdate(testResult)

    # create the 'ensemble' plot
    if len(dataDisplay.timeSeriesList) > 1:
        plotBinary = actor.plotPhaseEnsemble([ts.key for ts in dataDisplay.timeSeriesList])
        plotId = plotsDB.create(TestResultPlot(plotBinary = plotBinary, description = f"Phase stability ensemble"))
        if plotId:
            testResult.plots.append(plotId)
            # update the TestResult record with the ensemble plot:
            testResult.timeStamp = datetime.now()
            testResult = resultsDB.createOrUpdate(testResult)
    
    # all finished:
    actor.finish()
    