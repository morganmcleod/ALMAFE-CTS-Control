from AMB.LODevice import LODevice
from AMB.AMBConnectionItf import AMBConnectionItf
from CTSDevices.PowerMeter.KeysightE441X import PowerMeter
from CTSDevices.WarmIFPlate.WarmIFPlate import WarmIFPlate
from CTSDevices.Common.BinarySearchController import BinarySearchController
from CTSDevices.PNA.PNAInterface import PNAInterface
from CTSDevices.PNA.AgilentPNA import FAST_CONFIG
from app.routers.ActionPublisher import asyncAddItem

from pydantic import BaseModel
from typing import Optional
import time
import asyncio

class RFPower(BaseModel):
    index: int = 0
    complete: bool = False
    paOutput: float = 0
    power: float = 0


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

    def autoRFPowerMeter(self, powerMeter: PowerMeter, target: float = -5.0) -> bool:
        try:
            loop = self.loop
        except:
            try:
                self.loop = asyncio.get_running_loop()
            except RuntimeError:
                self.loop = None
        if self.loop and self.loop.is_running():
            tasks = set()
            task = self.loop.create_task(self.__autoRFPowerMeter(powerMeter, target))
            tasks.add(task)
            task.add_done_callback(tasks.discard)            
        else:
            asyncio.run(self.__autoRFPowerMeter(powerMeter, target))
        return True

    async def __autoRFPowerMeter(self, powerMeter: PowerMeter, target: float) -> bool:
        self.logger.info(f"target on power meter = {target} dBm")
        setValue = 20

        controller = BinarySearchController(
            outputRange = [0, 100], 
            initialStepPercent = 20, 
            initialOutput = setValue, 
            setPoint = target,
            tolerance = 1.5,
            maxIter = 20)

        self.setPAOutput(self.paPol, setValue)
        power = powerMeter.read()
        if not power:
            return False
        await asyncAddItem(RFPower(index = 0, paOutput = setValue, power = power))

        tprev = time.time()
        tsum = 0
        done = False
        while not done:
            controller.process(power)
            if controller.isComplete():
                await asyncAddItem(RFPower(index = controller.iter, complete = True))
                done = True
            else:
                setValue = controller.output
                self.setPAOutput(self.paPol, setValue)
                power = powerMeter.read()
                await asyncAddItem(RFPower(index = controller.iter, paOutput = setValue, power = power))
                self.logger.info(f"iter={controller.iter} setValue={setValue:.1f}%, power={power:.2f} dBm")

            tsum += (time.time() - tprev)
            tprev = time.time()

        iterTime = tsum / (controller.iter + 1)
        self.logger.info(f"RFSource.__autoRFPowerMeter: setValue={setValue:.1f}%, power={power:.2f} dBm, iter={controller.iter} iterTime={round(iterTime, 2)} success={controller.success} fail={controller.fail}")
        return controller.success

    def autoRFPNA(self, pna: PNAInterface, target: float = -5.0) -> bool:
        try:
            loop = self.loop
        except:
            try:
                self.loop = asyncio.get_running_loop()
            except RuntimeError:
                self.loop = None
        if self.loop and self.loop.is_running():
            tasks = set()
            task = self.loop.create_task(self.__autoRFPNA(pna, target))
            tasks.add(task)
            task.add_done_callback(tasks.discard)            
        else:
            asyncio.run(self.__autoRFPNA(pna, target))
        return True

    async def __autoRFPNA(self, pna: PNAInterface, target: float) -> bool:
        self.logger.info(f"target on PNA = {target} dB")
        setValue = 20 # percent
        pna.setMeasConfig(FAST_CONFIG)
        
        controller = BinarySearchController(
            outputRange = [0, 100], 
            initialStepPercent = 20, 
            initialOutput = setValue, 
            setPoint = target,
            tolerance = 1.5,
            maxIter = 20)
        
        self.setPAOutput(self.paPol, setValue)
        power, _ = pna.getAmpPhase()
        if not power:
            return False
        await asyncAddItem(RFPower(index = 0, paOutput = setValue, power = power))

        tprev = time.time()
        tsum = 0
        done = False
        while not done:
            controller.process(power)
            if controller.isComplete():
                await asyncAddItem(RFPower(index = controller.iter, complete = True))
                done = True
            else:
                setValue = controller.output
                self.setPABias(self.paPol, setValue)
                power, _ = pna.getAmpPhase()
                await asyncAddItem(RFPower(index = controller.iter, paOutput = setValue, power = power))
                self.logger.info(f"iter={controller.iter} setValue={setValue:.1f}%, power={power:.2f}")

            tsum += (time.time() - tprev)
            tprev = time.time()

        iterTime = tsum / (controller.iter + 1)
        self.logger.info(f"RFSource.__autoRFPNA: setValue={setValue:.1f}%, power={power:.2f} dBM, iter={controller.iter} iterTime={round(iterTime, 2)} success={controller.success} fail={controller.fail}")
        return controller.success
