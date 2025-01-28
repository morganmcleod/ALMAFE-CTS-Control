import typing
import time
from statistics import mean
from .Interface import SISMagnet_Interface, ResultsInterface
from Measure.MixerTests import ResultsQueue
from Measure.Shared.SelectSIS import SelectSIS
from INSTR.CurrentSource.Keithley24XX import CurrentSource, CurrentRange, CurrentLevel
from AMB.schemas.MixerTests import *
from Controllers.SIS.Interface import SISBias_Interface

class SISMagnet(SISMagnet_Interface):

    def __init__(self,
            currentSource: CurrentSource,            
            simulate: bool = False
        ):
        self.currentSource = currentSource
        self.simulate = simulate
        self.currentSource.setRearTerminals()
        self.currentSource.setOutput(True)
        self.stopNow = False
    
    def __del__(self):
        self.currentSource.setOutput(False)

    def setCurrent(self,
            currentMA: float,
            sisSelect: SelectSIS = SelectSIS.SIS1
        ) -> tuple[bool, str]:
        # only implement SIS1:
        if sisSelect == SelectSIS.SIS1:
            self.currentSource.setCurrentSource(currentMA / 1000, 0.1, CurrentRange.BY_VALUE)
            self.currentSource.setOutput(True)
        return True, ""
    
    def readCurrent(self,
            averaging: int = 1,
            sisSelect: SelectSIS = SelectSIS.SIS1
        ) -> float:
        return 1000 * self.currentSource.readCurrent(averaging)
    
    def stop(self):
        self.stopNow = True

    def magnetOptimize(self,
            settings: MagnetOptSettings,
            resultsTarget: ResultsInterface,
            sisBias: SISBias_Interface
        ) -> tuple[bool, str]:
        
        self.stopNow = False
        settings.sort()

        success, msg = settings.is_valid()
        if not success:
            return False, msg

        # mixer voltages off:
        sisBias.set_bias(SelectSIS.BOTH, 0)

        if settings.enableSis1:
            resultsTarget.put(0, 1, MagentOptPoint(), ResultsQueue.PointType.START)        
        if settings.enableSis2:
            resultsTarget.put(0, 2, MagentOptPoint(), ResultsQueue.PointType.START)

        iMagSet = settings.iMagStart
        stepPositive = settings.iMagStep >= 0
        done = False
        while not done and not self.stopNow:
            # test end condition here to be sure to get final points:
            if (stepPositive and iMagSet >= settings.iMagStop) or (not stepPositive and iMagSet <= settings.iMagStep):
                done = True
            elif settings.iMagStart == settings.iMagStop or settings.iMagStep == 0:
                done = True

            self.setCurrent(iMagSet)
            C01, C02 = self._measureICritical(settings, sisBias)

            if settings.enableSis1:
                resultsTarget.put(0, 1,
                    MagentOptPoint(
                        iMagSet = iMagSet,
                        ijRead = C01
                    )
                )
            if settings.enableSis2:
                resultsTarget.put(0, 2,
                    MagentOptPoint(
                        iMagSet = iMagSet,
                        ijRead = C02
                    )
                )            
            iMagSet += settings.iMagStep

        resultsTarget.put(0, 1, MagentOptPoint(), ResultsQueue.PointType.ALL_DONE)
        return True, ""

    def _measureICritical(self, settings: MagnetOptSettings, sisBias: SISBias_Interface) -> tuple[float, float]:
        # loop on VjSteps:
        vjSet = settings.vjStart
        stepPositive = settings.vjStep >= 0
        IJ1 = []
        IJ2 = []
        done = False
        while not done:
            sisBias.set_bias(SelectSIS.BOTH, vjSet)
            time.sleep(0.01)
            _, Ij = sisBias.read_bias(SelectSIS.SIS1)
            IJ1.append(Ij)
            _, Ij = sisBias.read_bias(SelectSIS.SIS2)
            IJ2.append(Ij)

            vjSet += settings.vjStep
            if (stepPositive and vjSet > settings.vjStop) or (not stepPositive and vjSet < settings.vjStop):
                done = True
            elif (settings.vjStop == settings.vjStart) or settings.vjStep == 0:
                done = True
        
        if settings.vjStop == settings.vjStart or settings.vjStep == 0:
            # not stepping.  Just return the max Ij:
            C01 = 1000 * max(IJ1)
            C02 = 1000 * max(IJ2)
        else: 
            # critical current is max - min seen at any of the swept voltages:
            C01 = 1000 * (max(IJ1) - min(IJ1))
            C02 = 1000 * (max(IJ2) - min(IJ2))
        return C01, C02
    
    def mixersDeflux(self,
            settings: DefluxSettings,
            resultsTarget: ResultsInterface
        ) -> tuple[bool, str]:
        # stepping iMag 0, +1, -1, +2, -2 ... +1, -1, 0
        # will hold stepSleep at each value:
        stepSleep = 0.95
        numSteps = int(settings.iMagMax / settings.iMagStep) + 1
        iMag = 0
        iMags = [0]
        for i in range(1, numSteps):
            iMag += settings.iMagStep
            iMags += [iMag, iMag, -iMag, -iMag]
        iMags += reversed(iMags[:-2])

        # get starting tMixers so we can detect cooldown at end:
        mixerTempsStart = self.getCartridgeTemps()

        # log headers
        self.logger.info(f"Mixers Deflux algorithm {settings.algorithm} {resultsTarget.curves[0].headers()}")
        
        # warm up the mixer above the heatingTemperature
        # then cycle through the iMag steps
        iMagStep = 0
        step = 0
        timeout = False
        # when we will give up on mixer heating and fail:
        endTime = time.time() + 60
        while not timeout and iMagStep < len(iMags):
            if settings.enablePol0:
                self.setSISHeater(0, False)
                self.setSISHeater(0, True)
            if settings.enablePol1:
                self.setSISHeater(1, False)
                self.setSISHeater(1, True)
            
            mixerTemps = self.getCartridgeTemps()
            ready0 = not settings.enablePol0
            ready1 = not settings.enablePol1
            
            if settings.enablePol0:
                resultsTarget.curves[0].points.append(
                    DefluxPoint(
                        step = step,
                        iMag = iMags[iMagStep],
                        tMixer = mixerTemps['temp2']
                    )
                )
                if mixerTemps['temp2'] >= settings.heatingTemperature:
                    ready0 = True

            if settings.enablePol1:
                resultsTarget.curves[1].points.append(
                    DefluxPoint(
                        step = step,
                        iMag = iMags[iMagStep],
                        tMixer = mixerTemps['temp5']
                    )
                )
                if mixerTemps['temp5'] >= settings.heatingTemperature:
                    ready1 = True
            
            if ready0 and ready1:
                if settings.enablePol0:
                    self.setSIS(0, 1, None, iMags[iMagStep])
                if settings.enablePol1:
                    self.setSIS(1, 1, None, iMags[iMagStep])
                iMagStep += 1
            else:
                timeout = time.time() > endTime
            
            if settings.enablePol0:
                self.logger.info(resultsTarget.curves[0].getRow())
            if settings.enablePol1:
                self.logger.info(resultsTarget.curves[1].getRow())
            step += 1
            time.sleep(stepSleep)

        if settings.enablePol0:
            self.setSIS(0, 1, 0, 0)
        if settings.enablePol1:
            self.setSIS(1, 2, 0, 0)

        # now wait for temperature to return to previously:
        mixerTempFinish = max(mixerTempsStart['temp2'], mixerTempsStart['temp5']) + 0.2
        done = False
        endTime = time.time() + 60
        while not done:
            time.sleep(stepSleep)            
            mixerTemps = self.getCartridgeTemps()
            if settings.enablePol0:
                resultsTarget.curves[0].points.append(
                    DefluxPoint(
                        step = step,
                        iMag = iMags[-1],
                        tMixer = mixerTemps['temp2']
                    )
                )
                self.logger.info(resultsTarget.curves[0].getRow())
            if settings.enablePol1:
                resultsTarget.curves[1].points.append(
                    DefluxPoint(
                        step = step,
                        iMag = iMags[-1],
                        tMixer = mixerTemps['temp5']
                    )
                )
                self.logger.info(resultsTarget.curves[1].getRow())
            
            done = (mixerTemps['temp2'] <= mixerTempFinish and mixerTemps['temp5'] <= mixerTempFinish) or time.time() > endTime
            step += 1

        if settings.enablePol0:
            resultsTarget.curves[0].finished = True
        if settings.enablePol1:
            resultsTarget.curves[1].finished = True
        if timeout:
            self.logger.error("Mixers Deflux: Timeout.")
            return resultsTarget.fail("timeout")
        else:
            self.logger.info("Mixers Deflux: Finished successfully.")          
            return resultsTarget.succeed()
        