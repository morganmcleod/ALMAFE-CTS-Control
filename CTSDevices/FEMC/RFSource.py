from AMB.LODevice import LODevice
from AMB.AMBConnectionItf import AMBConnectionItf
from CTSDevices.PowerMeter.KeysightE441X import PowerMeter
from CTSDevices.WarmIFPlate.YIGFilter import YIGFilter
from CTSDevices.Common.BinarySearchController import BinarySearchController
from CTSDevices.PNA.PNAInterface import PNAInterface
from CTSDevices.PNA.AgilentPNA import FAST_CONFIG

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
                yigFilter: YIGFilter, 
                freqIFGHz: float, 
                target: float = -5.0, 
                onThread: bool = False) -> bool:
        
        yigFilter.setFrequency(freqIFGHz)        
        if onThread:
            threading.Thread(target = self.__autoRFPowerMeter, args = (powerMeter, target), daemon = True).start()
            return True
        else:
            return self.__autoRFPowerMeter(powerMeter, target)

    def __autoRFPowerMeter(self, powerMeter: PowerMeter, target: float) -> bool:
        self.logger.info(f"target on power meter = {target} dBM")
        setVD = 0.7

        controller = BinarySearchController(
            outputRange = [0, 2.5], 
            initialStep = 0.1, 
            initialOutput = setVD, 
            setPoint = target,
            tolerance = 0.5,
            maxIter = 30)

        self.setPABias(self.paPol, setVD)

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
                setVD = controller.output
                self.setPABias(self.paPol, setVD)
                power = powerMeter.read()

            self.logger.info(f"iter={controller.iter} VD={setVD:.3f} power={power:.2f}")

            tsum += (time.time() - tprev)
            tprev = time.time()

        iterTime = tsum / (controller.iter + 1)
        self.logger.info(f"RFSource.__autoRFPowerMeter: setVD={setVD:.3f} mV, power={power:.2f} dBM, iter={controller.iter} iterTime={round(iterTime, 2)} success={controller.success} fail={controller.fail}")
        return controller.success

    def autoRFPNA(self, 
            pna: PNAInterface, 
            yigFilter: YIGFilter, 
            freqIFGHz: float, 
            target: float = -5.0, 
            onThread: bool = False) -> bool:
        
        yigFilter.setFrequency(freqIFGHz)
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
            outputRange = [15, 100], 
            initialStep = 0.1, 
            initialOutput = setValue, 
            setPoint = target,
            tolerance = 1,
            maxIter = 30)
        
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
                setVD = controller.output
                self.setPABias(self.paPol, setVD)
                power, _ = pna.getAmpPhase()

            self.logger.info(f"iter={controller.iter} VD={setVD:.3f} power={power:.2f}")

            tsum += (time.time() - tprev)
            tprev = time.time()

        iterTime = tsum / (controller.iter + 1)
        self.logger.info(f"RFSource.__autoRFPNA: setVD={setVD:.3f} mV, power={power:.2f} dBM, iter={controller.iter} iterTime={round(iterTime, 2)} success={controller.success} fail={controller.fail}")
        return controller.success
