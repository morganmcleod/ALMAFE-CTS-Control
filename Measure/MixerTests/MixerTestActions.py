import logging
import threading
import queue
import time
from DBBand6Cart.schemas.DUT_Type import DUT_Type
from INSTR.Chopper.Interface import Chopper_Interface
from INSTR.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from AMB.schemas.MixerTests import *
from AMB.CCADevice import IFPowerInterface
from Controllers.Receiver.CartAssembly import CartAssembly
from Controllers.Receiver.MixerAssembly import MixerAssembly
from Controllers.IFSystem.Interface import IFSystem_Interface
from Measure.Shared.MeasurementStatus import MeasurementStatus
from Measure.Shared.DataDisplay import DataDisplay
from Measure.Shared.SelectPolarization import SelectPolarization
from Measure.MixerTests.SettingsContainer import SettingsContainer
from Measure.MixerTests import ResultsQueue

class MixerTestActions():
    def __init__(self,
            dutType: DUT_Type,
            receiver: CartAssembly | MixerAssembly,
            ifSystem: IFSystem_Interface,
            tempMonitor: TemperatureMonitor,
            chopper: Chopper_Interface,
            measurementStatus: MeasurementStatus,
            dataDisplay: DataDisplay):
        
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.receiver = receiver
        self.ifSystem = ifSystem
        self.tempMonitor = tempMonitor
        self.chopper = chopper
        self.measurementStatus = measurementStatus
        self.dataDisplay = dataDisplay
        self.dutType = dutType
        self.ivCurveQueue = ResultsQueue.ResultsQueue(queue2 = self.dataDisplay.ivCurveQueue)
        self.magnetOptQueue = ResultsQueue.ResultsQueue(queue2 = self.dataDisplay.magnetOptQueue)
        self.defluxQueue = ResultsQueue.ResultsQueue(queue2 = self.dataDisplay.defluxQueue)
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
        self.receiver.settings.loSettings.lockLO = lockLO
        msg = "Locking" if lockLO else "Tuning"
        msg += f" LO at {freqLO:.2f} GHz..."
        self.measurementStatus.setStatusMessage(msg)
        success, msg = self.receiver.setFrequency(freqLO, self.receiver.settings.loSettings)

        if not success:
            self.logger.error(msg)
        elif msg:
            self.logger.info(msg)

        if setBias:
            success = self.receiver.setBias(freqLO)
            if not success:
                return False, "setBias failed. Provide config ID?"
            
        if loPumped:
            self.measurementStatus.setStatusMessage(f"Setting LO power...")
            pol0 = self.settings.ivCurveSettings.enable01 or self.settings.ivCurveSettings.enable02
            pol1 = self.settings.ivCurveSettings.enable11 or self.settings.ivCurveSettings.enable12
            success, msg = self.receiver.autoLOPower(pol0 = pol0, pol1 = pol1, on_thread = False)
            if not success:
                return False, "receiver.autoLOPower failed"

        if self.receiver.isLocked():
            return True, f"Locked LO {'and set bias ' if setBias else ''}at {freqLO:.2f} GHz."
        elif lockLO:
            return True, f"LO LOCK FAILED {'and set bias ' if setBias else ''}at {freqLO:.2f} GHz."
        else:
            return True, f"Tuned LO {'and set bias ' if setBias else ''}at {freqLO:.2f} GHz."

    def getLO(self) -> float:
        return self.receiver.freqLOGHz
    
    def measureIVCurves(self, 
            settings: IVCurveSettings, 
            resultsTarget: IVCurveResults,
            ifPowerImpl: IFPowerInterface | None = None
        ) -> IVCurveResults:
        self.measurementStatus.setStatusMessage(f"Measuring I-V Curves...")
        resultsTarget.reset()
        worker = threading.Thread(target = self.receiver.ivCurve, args = (settings, self.ivCurveQueue, ifPowerImpl, self.ifSystem, self.chopper), daemon = True)
        worker.start()
        done = False
        while not done:
            try:
                # get a queue item from the measurement thread:
                item: ResultsQueue.Item = self.ivCurveQueue.get_nowait()
                # populate resultsTarget:
                curve = resultsTarget.getCurve(item.pol, item.sis)
                if item.type == ResultsQueue.PointType.ALL_DONE:
                    done = True
                if item.points:
                    curve.points += item.points
            except queue.Empty:
                time.sleep(0.1)
        worker.join(timeout = 10)
        return resultsTarget

    def magnetOptimize(self,
            settings: MagnetOptSettings,
            resultsTarget: MagnetOptResults
        ) -> MagnetOptResults:
        
        self.measurementStatus.setStatusMessage(f"Measuring Magnet Optimization...")
        resultsTarget.reset()
        worker = threading.Thread(target = self.receiver.magnetOptimize, args = (settings, self.magnetOptQueue), daemon = True)
        worker.start()
        done = False
        while not done:
            try:
                if self.measurementStatus.stopNow():
                    self.receiver.stop()
                # get a queue item from the measurement thread:
                item: ResultsQueue.Item = self.magnetOptQueue.get_nowait()
                # populate resultsTarget:
                curve = resultsTarget.getCurve(item.pol, item.sis)
                if item.type == ResultsQueue.PointType.ALL_DONE:
                    done = True
                if item.points:
                    curve.points += item.points
            except queue.Empty:
                time.sleep(0.1)
        worker.join(timeout = 10)
        return resultsTarget
    
    def mixersDeflux(self, 
            settings: DefluxSettings, 
            resultsTarget: DefluxResults = None
        ) -> DefluxResults:
        
        self.measurementStatus.setStatusMessage(f"Defluxing mixers...")
        # turn off the LO:
        self.receiver.setPAOutput(SelectPolarization.POL0, 0)
        self.receiver.setPAOutput(SelectPolarization.POL1, 0)
        resultsTarget.reset()
        worker = threading.Thread(target = self.receiver.mixersDeflux, args = (settings, self.defluxQueue), daemon = True)
        worker.start()
        done = False
        while not done:
            try:
                # get a queue item from the measurement thread:
                item: ResultsQueue.Item = self.defluxQueue.get_nowait()
                # populate resultsTarget:
                curve = resultsTarget.curves[item.pol]
                if item.type == ResultsQueue.PointType.ALL_DONE:
                    done = True
                if item.points:
                    curve.points += item.points
            except queue.Empty:
                time.sleep(0.1)
        worker.join(timeout = 10)
        return resultsTarget