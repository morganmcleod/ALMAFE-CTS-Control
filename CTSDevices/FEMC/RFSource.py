from AMB.LODevice import LODevice
from AMB.AMBConnectionItf import AMBConnectionItf
from CTSDevices.PowerMeter.KeysightE441X import PowerMeter
from CTSDevices.PowerMeter.Simulator import PowerMeterSimulator
from CTSDevices.WarmIFPlate.WarmIFPlate import WarmIFPlate
from CTSDevices.Common.BinarySearchController import BinarySearchController
from CTSDevices.PNA.PNAInterface import PNAInterface
from CTSDevices.PNA.AgilentPNA import FAST_CONFIG
from app.routers.AppEvents import Event, addEvent

from typing import Optional, Union
import time
import threading

class RFSource(LODevice):
    def __init__(
            self, 
            conn: AMBConnectionItf, 
            nodeAddr: int, 
            band: int,                      # what band is the actual hardware
            femcPort:Optional[int] = None,  # optional override which port the band is connected to)
            paPol: int = 0                  # which polarization to operate for the RF source
        ):
        super(RFSource, self).__init__(conn, nodeAddr, band, femcPort)
        self.paPol = paPol

    def autoRFPower(self, meter: Union[PowerMeter, PNAInterface], target: float = -5.0, onThread: bool = False) -> bool:
        if onThread:
            threading.Thread(target = self.__autoRFPower, args = (meter, target), daemon = True).start()
            return True
        else:
            return self.__autoRFPower(meter, target)

    def __autoRFPower(self, meter: Union[PowerMeter, PNAInterface], target: float) -> bool:
        if isinstance(meter, PowerMeter) or isinstance(meter, PowerMeterSimulator):
            isPowerMeter = True
        else:
            isPowerMeter = False

        self.logger.info(f"target receive on {'Power Meter' if isPowerMeter else 'PNA'}: {target} dBm")
        setValue = 20

        controller = BinarySearchController(
            outputRange = [0, 100], 
            initialStepPercent = 20, 
            initialOutput = setValue, 
            setPoint = target,
            tolerance = 1.5,
            maxIter = 20)

        self.setPAOutput(self.paPol, setValue)
        if isPowerMeter:
            power = meter.read()
        else:
            power, _ = meter.getAmpPhase()
        if not power:
            return False
        addEvent(Event(type = "rfPower", iter = 0, x = setValue, y = power))

        tprev = time.time()
        tsum = 0
        done = False
        while not controller.isComplete():
            controller.process(power)
            setValue = controller.output
            self.setPAOutput(self.paPol, setValue)
            if isPowerMeter:
                power = meter.read()
            else:
                power, _ = meter.getAmpPhase()
            addEvent(Event(type = "rfPower", iter = controller.iter, x = setValue, y = power))
            self.logger.info(f"iter={controller.iter} setValue={setValue:.1f}%, power={power:.2f} dBm")
            tsum += (time.time() - tprev)
            tprev = time.time()

        addEvent(Event(type = "rfPower", iter = "complete"))

        iterTime = tsum / (controller.iter + 1)
        self.logger.info(f"RFSource.__autoRFPower: setValue={setValue:.1f}%, power={power:.2f} dBm, iter={controller.iter} iterTime={round(iterTime, 2)} success={controller.success}")
        return controller.success
  