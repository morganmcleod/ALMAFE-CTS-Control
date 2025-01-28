from INSTR.DMM.HP34401 import HP34401
from INSTR.DMM.VoltMeterSimulator import VoltMeterSimulator
from DebugOptions import *

if SIMULATE:
    voltMeter = VoltMeterSimulator()
else:
    voltMeter = HP34401("GPIB0::22::INSTR")

