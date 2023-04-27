from CTSDevices.SignalGenerator.Keysight_PSG_MXG import SignalGenerator
from CTSDevices.SignalGenerator.Simulator import SignalGenSimulator
from .debugging import *

if SIMULATE:
    loReference = SignalGenSimulator()
    rfReference = SignalGenSimulator()
else:    
    loReference = SignalGenerator("GPIB0::19::INSTR", reset = False)
    rfReference = SignalGenerator("GPIB0::17::INSTR", reset = False)