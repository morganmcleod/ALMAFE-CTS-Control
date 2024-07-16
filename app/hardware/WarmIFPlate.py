from INSTR.WarmIFPlate.Attenuator import Attenuator
from INSTR.InputSwitch.InputSwitch import InputSwitch
from INSTR.InputSwitch.ExternalSwitch import ExternalSwitch
from INSTR.WarmIFPlate.NoiseSource import NoiseSource
from INSTR.WarmIFPlate.OutputSwitch import OutputSwitch
from INSTR.WarmIFPlate.YIGFilter import YIGFilter
from INSTR.WarmIFPlate.WarmIFPlate import WarmIFPlate

from DebugOptions import *

if SIMULATE:
    warmIFPlate = WarmIFPlate(
        Attenuator(simulate = True),
        InputSwitch(simulate = True),
        NoiseSource(simulate = True),
        OutputSwitch(simulate = True),
        YIGFilter(simulate = True)
    )
else:
    warmIFPlate = WarmIFPlate(
        Attenuator(resource = "GPIB0::28::INSTR"),
        InputSwitch(resource = "GPIB0::9::INSTR"),
        NoiseSource(resource = "GPIB0::5::INSTR"),
        OutputSwitch(resource = "GPIB0::9::INSTR"),
        YIGFilter(resource = "GPIB0::9::INSTR"))

externalSwitch = ExternalSwitch("GPIB0::29::INSTR", SIMULATE)
