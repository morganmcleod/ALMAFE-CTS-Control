from AMB.LODevice import LODevice
from AMB.AMBConnectionItf import AMBConnectionItf
from INSTR.PowerMeter.KeysightE441X import PowerMeter
from INSTR.PowerMeter.Simulator import PowerMeterSimulator
from .BinarySearchController import BinarySearchController
from INSTR.PNA.PNAInterface import PNAInterface
from INSTR.PNA.AgilentPNA import FAST_CONFIG, DEFAULT_POWER_CONFIG
from INSTR.SignalGenerator.Interface import SignalGenInterface

from typing import Optional, Union, Tuple
import time
import threading
from DebugOptions import *

class RFSource(LODevice):
    def __init__(
            self, 
            conn: AMBConnectionItf, 
            nodeAddr: int, 
            band: int,                      # what band is the actual hardware
            femcPort:Optional[int] = None,  # optional override which port the band is connected to)
            paPol: int = 0                  # which polarization to operate for the RF source
        ):
        super().__init__(conn, nodeAddr, band, femcPort)
        self.paPol = paPol
        self.setPAOutput(self.paPol, 0)
        self.autoRfPowerValue = None            # for websocket reporting to client

    def isConnected(self) -> bool:
        return super().isConnected()
    
    def lockRF(self, rfReference: SignalGenInterface, freqRF: float, sigGenAmplitude: float = 10.0) -> Tuple[bool, str]:
        self.selectLockSideband(self.LOCK_ABOVE_REF)
        wcaFreq, ytoFreq, ytoCourse = self.setLOFrequency(freqRF)
        if wcaFreq == 0:
            return False, "lockRF: frequency out of range"
        pllConfig = self.getPLLConfig()
        rfReference.setFrequency((freqRF / pllConfig['coldMult'] - 0.020) / pllConfig['warmMult'])
        rfReference.setAmplitude(sigGenAmplitude)
        rfReference.setRFOutput(True)
        if not SIMULATE:
            wcaFreq, ytoFreq, ytoCourse = self.lockPLL()
            success = wcaFreq != 0
        else:
            self.setNullLoopIntegrator(True)
            success = True
        return success, f"lockRF: wca={wcaFreq}, yto={ytoFreq}, courseTune={ytoCourse}"

    def getPAVD(self):
        pa = self.getPA()
        if self.paPol == 0:
            return pa['VDp0']
        elif self.paPol == 1:
            return pa['VDp1']

    def setPAOutput(self, pol: int, percent: float):
        self._paOutput = percent
        return super().setPAOutput(pol, percent)
    
    def getPAOutput(self) -> float:
        return self._paOutput

    def autoRFPower(self, meter: Union[PowerMeter, PNAInterface], target: float = -5.0, onThread: bool = False) -> bool:
        if onThread:
            threading.Thread(target = self.__autoRFPower, args = (meter, target), daemon = True).start()
            return True
        else:
            return self.__autoRFPower(meter, target)

    def __autoRFPower(self, meter: Union[PowerMeter, PNAInterface], target: float) -> bool:
        if isinstance(meter, PowerMeter) or isinstance(meter, PowerMeterSimulator):
            isPowerMeter = True
            units = "dBm"
        else:
            isPowerMeter = False
            meter.setPowerConfig(DEFAULT_POWER_CONFIG)
            meter.setMeasConfig(FAST_CONFIG)
            units = "dB"

        self.logger.info(f"target receive on {'Power Meter' if isPowerMeter else 'PNA'}: {target} {units}")
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
            self.autoRfPowerValue = meter.read()
        else:
            self.autoRfPowerValue, _ = meter.getAmpPhase()
        if not self.autoRfPowerValue:
            return False

        tprev = time.time()
        tsum = 0
        while not controller.isComplete():
            controller.process(self.autoRfPowerValue)
            setValue = controller.output
            self.setPAOutput(self.paPol, setValue)
            time.sleep(0.1)
            if isPowerMeter:
                self.autoRfPowerValue = meter.read()
            else:
                self.autoRfPowerValue, _ = meter.getAmpPhase()
            self.logger.info(f"iter={controller.iter} setValue={setValue:.1f}%, power={self.autoRfPowerValue:.2f} {units}")
            tsum += (time.time() - tprev)
            tprev = time.time()

        iterTime = tsum / (controller.iter + 1)
        self.logger.info(f"RFSource.__autoRFPower: setValue={setValue:.1f}%, power={self.autoRfPowerValue:.2f} {units}, iter={controller.iter} iterTime={round(iterTime, 2)} success={controller.success}")
        self.autoRfPowerValue = None
        return controller.success
  