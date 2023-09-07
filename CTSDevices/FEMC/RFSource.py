from AMB.LODevice import LODevice
from AMB.AMBConnectionItf import AMBConnectionItf
from CTSDevices.PowerMeter.KeysightE441X import PowerMeter
from CTSDevices.WarmIFPlate.WarmIFPlate import WarmIFPlate
from CTSDevices.Common.BinarySearchController import BinarySearchController
from CTSDevices.PNA.PNAInterface import PNAInterface
from CTSDevices.PNA.AgilentPNA import FAST_CONFIG
from CTSDevices.WarmIFPlate.OutputSwitch import PadSelect, LoadSelect, OutputSelect

from typing import Optional
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

    def autoRFPowerMeter(self, 
                powerMeter: PowerMeter, 
                warmIFPlate: WarmIFPlate, 
                freqIFGHz: float, 
                target: float = -5.0, 
                onThread: bool = False) -> bool:
        
        warmIFPlate.outputSwitch.setValue(OutputSelect.POWER_METER, LoadSelect.THROUGH, PadSelect.PAD_OUT)        
        warmIFPlate.attenuator.setValue(22)
        warmIFPlate.yigFilter.setFrequency(freqIFGHz)
        if onThread:
            threading.Thread(target = self.__autoRFPowerMeter, args = (powerMeter, target), daemon = True).start()
            return True
        else:
            return self.__autoRFPowerMeter(powerMeter, target)

    def __autoRFPowerMeter(self, powerMeter: PowerMeter, target: float) -> bool:
        self.logger.info(f"target on power meter = {target} dBm")
        setValue = 15

        controller = BinarySearchController(
            outputRange = [0, 100], 
            initialStep = 0.1, 
            initialOutput = setValue, 
            setPoint = target,
            tolerance = 0.5,
            maxIter = 20)

        self.setPAOutput(self.paPol, setValue)

        power = powerMeter.read()

        if not power:
            return False

        tprev = time.time()
        tsum = 0
        done = False
        while not done:
            controller.process(power)
            if controller.isComplete():
                done = True
            else:
                setValue = controller.output
                self.setPAOutput(self.paPol, setValue)
                power = powerMeter.read()

            self.logger.info(f"iter={controller.iter} setValue={setValue:.1f}%, power={power:.2f} dBm")

            tsum += (time.time() - tprev)
            tprev = time.time()

        iterTime = tsum / (controller.iter + 1)
        self.logger.info(f"RFSource.__autoRFPowerMeter: setValue={setValue:.1f}%, power={power:.2f} dBm, iter={controller.iter} iterTime={round(iterTime, 2)} success={controller.success} fail={controller.fail}")
        return controller.success

    def autoRFPNA(self, 
            pna: PNAInterface, 
            warmIFPlate: WarmIFPlate, 
            freqIFGHz: float, 
            target: float = -5.0, 
            onThread: bool = False) -> bool:
        
        # warmIFPlate.outputSwitch.setValue(OutputSelect.SQUARE_LAW, LoadSelect.THROUGH, PadSelect.PAD_OUT)        
        # warmIFPlate.attenuator.setValue(22)
        # warmIFPlate.yigFilter.setFrequency(freqIFGHz)
        if onThread:
            threading.Thread(target = self.__autoRFPNA, args = (pna, target), daemon = True).start()
            return True
        else:
            return self.__autoRFPNA(pna, target)

    def __autoRFPNA(self, pna: PNAInterface, target: float) -> bool:
        self.logger.info(f"target on PNA = {target} dB")
        setValue = 15 # percent
        pna.setMeasConfig(FAST_CONFIG)
        
        controller = BinarySearchController(
            outputRange = [0, 100], 
            initialStep = 0.1, 
            initialOutput = setValue, 
            setPoint = target,
            tolerance = 1,
            maxIter = 20)
        
        self.setPAOutput(self.paPol, setValue) 

        power, _ = pna.getAmpPhase()
        if not power:
            return False

        tprev = time.time()
        tsum = 0
        done = False
        while not done:
            controller.process(power)
            if controller.isComplete():
                done = True
            else:
                setValue = controller.output
                self.setPABias(self.paPol, setValue)
                power, _ = pna.getAmpPhase()

            self.logger.info(f"iter={controller.iter} setValue={setValue:.1f}%, power={power:.2f}")

            tsum += (time.time() - tprev)
            tprev = time.time()

        iterTime = tsum / (controller.iter + 1)
        self.logger.info(f"RFSource.__autoRFPNA: setValue={setValue:.1f}%, power={power:.2f} dBM, iter={controller.iter} iterTime={round(iterTime, 2)} success={controller.success} fail={controller.fail}")
        return controller.success
