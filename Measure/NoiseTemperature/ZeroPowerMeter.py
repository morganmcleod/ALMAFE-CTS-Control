
from CTSDevices.WarmIFPlate.OutputSwitch import OutputSelect, LoadSelect, PadSelect
from CTSDevices.PowerMeter.KeysightE441X import PowerMeter, Unit
from CTSDevices.WarmIFPlate.WarmIFPlate import WarmIFPlate
from ..Shared.MeasurementStatus import MeasurementStatus
import concurrent.futures
from DebugOptions import *
import logging

class ZeroPowerMeter():

    def __init__(self,
            warmIFPlate: WarmIFPlate, 
            powerMeter: PowerMeter,
            measurementStatus: MeasurementStatus):
        
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.warmIFPlate = warmIFPlate
        self.powerMeter = powerMeter
        self.measurementStatus = measurementStatus
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers = 1)
        self.finished = True

    def start(self):
        self.finished = False
        self.measurementStatus.setComplete(False)
        self.futures = []
        self.futures.append(self.executor.submit(self.__run))
        self.measurementStatus.setStatusMessage("Zero Power Meter started")
        self.measurementStatus.setError(False)

    def stop(self):
        pass

    def isMeasuring(self):
        return not self.finished    

    def __run(self) -> None:
        
        self.powerMeter.setUnits(Unit.DBM)
        self.powerMeter.setFastMode(False)
        self.warmIFPlate.outputSwitch.setValue(OutputSelect.POWER_METER, LoadSelect.LOAD, PadSelect.PAD_OUT)
        self.powerMeter.zero()
        self.warmIFPlate.outputSwitch.setValue(OutputSelect.POWER_METER, LoadSelect.THROUGH, PadSelect.PAD_OUT)
        self.measurementStatus.setStatusMessage("Zero Power Meter stopped")
        self.measurementStatus.setComplete(True)
        self.finished = True
