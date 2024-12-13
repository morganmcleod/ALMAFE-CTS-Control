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
    calcDataDB = CalcDataAmplitudeStability(driver = CTSDB())
    timeSeriesAPI = TimeSeriesAPI()

    cart_test = measurementStatus.getMeasuring()
    assert(cart_test.fkTestType == TestTypeIds.AMP_STABILITY.value)
    receiver.setCartConfig(cart_test.configId)

    # DataSources are associated with a time series and control what is shown on plots
    dataSources = {}
    dataSources[DataSource.DATA_KIND] = DataKind.AMPLITUDE.value
    dataSources[DataSource.DATA_SOURCE] = f"Test ID {cart_test.key}"
    dataSources[DataSource.CONFIG_ID] = cart_test.configId
    dataSources[DataSource.SERIALNUM] = receiver.settings.serialNum        
    dataSources[DataSource.TEST_SYSTEM] = cart_test.testSysName
    dataSources[DataSource.UNITS] = pdVoltMeter.units.value
    dataSources[DataSource.T_UNITS] = Units.KELVIN.value
    dataSources[DataSource.OPERATOR] = cart_test.operator
    dataSources[DataSource.NOTES] = cart_test.description
    dataSources[DataSource.MEAS_SW_NAME] = "ALMAFE-CTS-Control"
    branch = gitBranch()
    commit = gitVersion(branch = branch)
    dataSources[DataSource.MEAS_SW_VERSION] = branch + ":" + commit[0:7]

    # Test result holds additional metadata about the measurement and a list of plot IDs
    testResult = TestResult(
        fkCartTests = cart_test.key,
        dataStatus = DataStatus.MEASURED,
        measurementSW = dataSources[DataSource.MEAS_SW_VERSION],
        description = cart_test.description,
        plots = []
    )
    resultsDB.create(testResult)

    # set the actor to use the VoltMeter for power detection:
    actor.setPowerDetect(pdVoltMeter)
    settings = settingsContainer.ampStability
    actor.start(settings)

    # set the IF attenuator:
    ifSystem.attenuation = settings.attenuateIF

    # need to save tau0Seconds for the ensemble plot:
    tau0Seconds = 0

    for freqLO in makeSteps(settings.loStart, settings.loStop, settings.loStep):
        if measurementStatus.stopNow():
            actor.stop()
            break
           
        actor.setLO(freqLO, setBias = True)
        if not receiver.isLocked():
            logger.warning(f"Amplitude Stability: LO not locked at {freqLO} GHz")

        actor.delayAfterLock()

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

                        # set up time series to collect amplitude vs time:
                        ampSeries = TimeSeries(startTime = datetime.now(), dataUnits = pdVoltMeter.units)
                        if tau0Seconds != 0:
                            tau0Seconds = ampSeries.tau0Seconds

                        # measure amplitude and ambient temperature vs. time:
                        success, msg = actor.measureAmplitude(ampSeries)
                        if not success:
                            logger.error(f"Amplitude Stability: {msg}")
                            continue

                        if measurementStatus.stopNow():
                            actor.stop()
                            break

                        # this stores metadata and plots associated with a time series
                        info = TimeSeriesInfo(
                            key = ampSeries.tsId,
                            freqLO = freqLO,
                            pol = pol,
                            sideband = sb,
                            timeStamp = datetime.now(),
                            dataStatus = DataStatus.PROCESSED.name,
                            tau0Seconds = ampSeries.tau0Seconds
                        )

                        # apply the dataSources to specify plot appearance:
                        dataSources[DataSource.LO_GHZ] = freqLO
                        dataSources[DataSource.SUBSYSTEM] = f"pol{pol} {sb}"
                        for key in dataSources.keys():
                            timeSeriesAPI.setDataSource(ampSeries.tsId, key, dataSources[key])
                        
                        # plot the amplitude time series:
                        plotBinary = actor.plotTimeSeries(ampSeries)
                        info.timeSeriesPlot = plotsDB.create(TestResultPlot(plotBinary = plotBinary, description = f"Time series LO={freqLO} Pol{pol} {sb}"))
                        if info.timeSeriesPlot:
                            testResult.plots.append(info.timeSeriesPlot)
                        
                        # plot amplitude stabliity Allan variance:
                        plotBinary, trace = actor.plotAmplitudeStability(ampSeries)
                        info.allanPlot = plotsDB.create(TestResultPlot(plotBinary = plotBinary, description = f"Amplitude stability LO={freqLO} Pol{pol} {sb}"))
                        if info.allanPlot:
                            testResult.plots.append(info.allanPlot)
                        # store the Allan trace in the database:
                        if trace:
                            records = traceToStabilityRecords(
                                trace,
                                cart_test.key,
                                ampSeries.tsId,
                                freqLO,
                                None,
                                pol,
                                sb
                            )
                            calcDataDB.create(records)

                        # plot the FFT:                        
                        plotBinary = actor.plotSpectrum(ampSeries)
                        info.spectrumPlot = plotsDB.create(TestResultPlot(plotBinary = plotBinary, description = f"Amplitude spectrum LO={freqLO} Pol{pol} {sb}"))
                        if info.spectrumPlot:
                            testResult.plots.append(info.spectrumPlot)

                        # add the TimeSeriesInfo record to the list for user display:
                        dataDisplay.timeSeriesList.append(info)

                        # update the TestResult record with the plots created so far:
                        testResult.timeStamp = datetime.now()
                        testResult = resultsDB.createOrUpdate(testResult)

    # create the 'ensemble' plot
    if len(dataDisplay.timeSeriesList) > 1:
        plotBinary = actor.plotAmplitudeEnsemble([ts.key for ts in dataDisplay.timeSeriesList], tau0Seconds = tau0Seconds)
        plotId = plotsDB.create(TestResultPlot(plotBinary = plotBinary, description = f"Amplitude stability ensemble"))
        if plotId:
            testResult.plots.append(plotId)
            # update the TestResult record with the ensemble plot:
            testResult.timeStamp = datetime.now()
            testResult = resultsDB.createOrUpdate(testResult)

    # all finished:
    actor.finish()
    