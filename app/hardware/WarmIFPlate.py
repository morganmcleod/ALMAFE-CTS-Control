from CTSDevices.WarmIFPlate.Attenuator import Attenuator
from CTSDevices.WarmIFPlate.InputSwitch import InputSwitch
from CTSDevices.WarmIFPlate.NoiseSource import NoiseSource
from CTSDevices.WarmIFPlate.OutputSwitch import OutputSwitch
from CTSDevices.WarmIFPlate.YIGFilter import YIGFilter
from CTSDevices.WarmIFPlate.Simulator import AttenuatorSimulator, InputSwitchSimulator, NoiseSourceSimulator, OutputSwitchSimulator, YIGFilterSimulator
from CTSDevices.WarmIFPlate.WarmIFPlate import WarmIFPlate
from CTSDevices.WarmIFPlate.ExternalSwitch import ExternalSwitch
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
