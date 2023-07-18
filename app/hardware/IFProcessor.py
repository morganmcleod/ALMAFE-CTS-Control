from CTSDevices.IFProcessor.Attenuator import Attenuator
from CTSDevices.IFProcessor.InputSwitch import InputSwitch
from CTSDevices.IFProcessor.NoiseSource import NoiseSource
from CTSDevices.IFProcessor.OutputSwitch import OutputSwitch
from CTSDevices.IFProcessor.YIGFilter import YIGFilter
from CTSDevices.IFProcessor.Simulator import AttenuatorSimulator, InputSwitchSimulator, NoiseSourceSimulator, OutputSwitchSimulator, YIGFilterSimulator
from CTSDevices.IFProcessor.IFProcessor import IFProcessor
from .DebugOptions import *


if SIMULATE:
    ifProcessor = IFProcessor(
        AttenuatorSimulator(),
        InputSwitchSimulator(),
        NoiseSourceSimulator(),
        OutputSwitchSimulator(),
        YIGFilterSimulator())
else:
    ifProcessor = IFProcessor(
        Attenuator(resource = "GPIB0::28::INSTR"),
        InputSwitch(resource = "GPIB0::9::INSTR"),
        NoiseSource(resource = "GPIB0::5::INSTR"),
        OutputSwitch(resource = "GPIB0::9::INSTR"),
        YIGFilter(resource = "GPIB0::9::INSTR"))
