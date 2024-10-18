import logging
import threading
from typing import Union
from DBBand6Cart.schemas.DUT_Type import DUT_Type
from INSTR.SignalGenerator.Keysight_PSG_MXG import SignalGenerator
from AMB.schemas.MixerTests import *
from AMB.CCADevice import IFPowerInterface
from Control.CartAssembly import CartAssembly
from Measure.Shared.MeasurementStatus import MeasurementStatus
from Measure.Shared.DataDisplay import DataDisplay
from Measure.Shared.makeSteps import makeSteps
from Measure.MixerTests.SettingsContainer import SettingsContainer

class MixerTestActions():

    def __init__(self,
            loReference: SignalGenerator,
            receiver: CartAssembly,
            measurementStatus: MeasurementStatus,
            dataDisplay: DataDisplay,
            dutType: DUT_Type):
        
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.loReference = loReference
        self.receiver = receiver
        self.measurementStatus = measurementStatus
        self.dataDisplay = dataDisplay
        self.dutType = dutType
        self._reset()

    def _reset(self) -> None:
        self.settings = None
        self.finished = False
        self.dataDisplay.reset()

    def start(self, settings: SettingsContainer):
        self.settings = settings
        self.measurementStatus.setComplete(False)
        self.measurementStatus.setStatusMessage("Started")

    def stop(self):        
        self.measurementStatus.stopMeasuring()

    def finish(self):
        self.settings = None
        self.measurementStatus.setComplete(True)
        self.measurementStatus.setMeasuring(None)
        self.measurementStatus.setStatusMessage("Finished")

    def setLO(self, 
            freqLO: float, 
            lockLO: bool = False, 
            loPumped: bool = True,
            setBias: bool = True,
        ) -> tuple[bool, str]:
        
        msg = None
        if lockLO:
            self.measurementStatus.setStatusMessage(f"Locking LO at {freqLO:.2f} GHz...")
            success, msg = self.receiver.lockLO(self.loReference, freqLO)
        else:
            self.measurementStatus.setStatusMessage(f"Tuning LO at {freqLO:.2f} GHz...")
            wcaFreq, _, _ = self.receiver.loDevice.setLOFrequency(freqLO)
            if wcaFreq == 0:
                success = False
                msg = "Error tuning LO"
            else:
                success = True
                self.receiver.loDevice.setNullLoopIntegrator(True)

        if not success:
            self.logger.error(msg)
        elif msg:
            self.logger.info(msg)

        if setBias:
            success = self.receiver.setRecevierBias(freqLO)
            if not success:
                return False, "setRecevierBias failed. Provide config ID?"
            
        if loPumped:
            self.measurementStatus.setStatusMessage(f"Setting LO power...")
            pol0 = self.settings.ivCurveSettings.enable01 or self.settings.ivCurveSettings.enable02
            pol1 = self.settings.ivCurveSettings.enable11 or self.settings.ivCurveSettings.enable12
            success = self.receiver.autoLOPower(pol0, pol1)
            if not success:
                return False, "cartAssembly.autoLOPower failed"

        if self.receiver.isLocked():
            return True, f"Locked LO {'and set bias ' if setBias else ''}at {freqLO:.2f} GHz."
        elif lockLO:
            return True, f"LO LOCK FAILED {'and set bias ' if setBias else ''}at {freqLO:.2f} GHz."
        else:
            return True, f"Tuned LO {'and set bias ' if setBias else ''}at {freqLO:.2f} GHz."

    def getLO(self) -> float:
        return self.receiver.freqLOGHz
    
    def measureIVCurve(self, 
            settings: IVCurveSettings, 
            ifPowerImpl: IFPowerInterface = None,
            onThread: bool = False,
            resultsTarget: IVCurveResults = None) -> IVCurveResults:

        if onThread:
            threading.Thread(target = self.receiver.ccaDevice.IVCurve, args = (settings, ifPowerImpl, resultsTarget), daemon = True).start()
        else:
            self.receiver.ccaDevice.IVCurve(settings, ifPowerImpl, resultsTarget)
        return resultsTarget
        
    def magnetOptimize(self,
            settings: MagnetOptSettings,
            onThread: bool = False,
            resultsTarget: MagnetOptResults = None) -> MagnetOptResults:
        
        # turn off the LO:
        if settings.enablePol0:
            self.receiver.loDevice.setPAOutput(0, 0)
        if settings.enablePol1:
            self.receiver.loDevice.setPAOutput(1, 0)
        if onThread:
            threading.Thread(target = self.receiver.ccaDevice.magnetOptimize, args = (settings, resultsTarget), daemon = True).start()
        else:
            self.receiver.ccaDevice.magnetOptimize(settings, resultsTarget)
        return resultsTarget
    
    def mixersDeflux(self, 
            settings: DefluxSettings, 
            onThread: bool = False,
            resultsTarget: DefluxResults = None) -> DefluxResults:
        
        # turn off the LO:
        if settings.enablePol0:
            self.receiver.loDevice.setPAOutput(0, 0)
        if settings.enablePol1:
            self.receiver.loDevice.setPAOutput(1, 0)
        if onThread:
            threading.Thread(target = self.receiver.ccaDevice.mixersDeflux, args = (settings, resultsTarget), daemon = True).start()
        else:
            self.receiver.ccaDevice.mixersDeflux(settings, resultsTarget)
        return resultsTarget