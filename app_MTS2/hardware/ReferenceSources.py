from INSTR.SignalGenerator.Keysight_PSG_MXG import SignalGenerator
from INSTR.SignalGenerator.Simulator import SignalGenSimulator
from DebugOptions import *

if SIMULATE:
    loReference = SignalGenSimulator()
    rfReference = SignalGenSimulator()
else:    
    loReference = SignalGenerator("TCPIP0::10.1.1.7::inst0::INSTR", reset = False)
    rfReference = SignalGenerator("TCPIP0::10.1.1.6::inst0::INSTR", reset = False)