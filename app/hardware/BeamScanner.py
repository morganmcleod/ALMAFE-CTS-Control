from CTSDevices.MotorControl.GalilDMCSocket import MotorController
from CTSDevices.MotorControl.MCSimulator import MCSimulator
from CTSDevices.PNA.schemas import MeasConfig, PowerConfig
from CTSDevices.PNA.AgilentPNA import AgilentPNA
from CTSDevices.PNA.PNASimulator import PNASimulator

from DebugOptions import *

if SIMULATE:
    motorController = MCSimulator()
else:
    motorController = MotorController()

if SIMULATE:
    pna = PNASimulator()
else:
    pna = AgilentPNA(resource="GPIB0::16::INSTR", idQuery=True, reset=True)
pna.setMeasConfig(MeasConfig())
pna.setPowerConfig(PowerConfig())
