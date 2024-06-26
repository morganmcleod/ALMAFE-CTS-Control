from INSTR.WarmIFPlate.Attenuator import Attenuator
from INSTR.WarmIFPlate.InputSwitch import InputSwitch
from INSTR.WarmIFPlate.NoiseSource import NoiseSource
from INSTR.WarmIFPlate.OutputSwitch import OutputSwitch
from INSTR.WarmIFPlate.YIGFilter import YIGFilter
from INSTR.WarmIFPlate.Simulator import AttenuatorSimulator, InputSwitchSimulator, NoiseSourceSimulator, OutputSwitchSimulator, YIGFilterSimulator
from INSTR.WarmIFPlate.WarmIFPlate import WarmIFPlate
from INSTR.WarmIFPlate.ExternalSwitch import ExternalSwitch
from DebugOptions import *

if SIMULATE:
    warmIFPlate = WarmIFPlate(
        AttenuatorSimulator(),
        InputSwitchSimulator(),
        NoiseSourceSimulator(),
        OutputSwitchSimulator(),
        YIGFilterSimulator())
else:
    warmIFPlate = WarmIFPlate(
        Attenuator(resource = "GPIB0::28::INSTR"),
        InputSwitch(resource = "GPIB0::9::INSTR"),
        NoiseSource(resource = "GPIB0::5::INSTR"),
        OutputSwitch(resource = "GPIB0::9::INSTR"),
        YIGFilter(resource = "GPIB0::9::INSTR"))

externalSwitch = ExternalSwitch("GPIB0::29::INSTR", SIMULATE)
