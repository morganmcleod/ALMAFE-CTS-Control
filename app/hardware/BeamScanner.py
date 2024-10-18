import configparser
from INSTR.MotorControl.GalilDMCSocket import MotorController
from INSTR.MotorControl.MCSimulator import MCSimulator
from INSTR.PNA.schemas import MeasConfig, PowerConfig
from INSTR.PNA.AgilentPNA import AgilentPNA
from INSTR.PNA.PNASimulator import PNASimulator

from DebugOptions import *

if SIMULATE:
    motorController = MCSimulator()
else:
    motorController = MotorController("10.1.1.20")
    # load specifics about the motor controller for this system:
    config = configparser.ConfigParser()
    config.read('ALMAFE-CTS-Control.ini')
    motorController.setStepping(
        config['MotorController']['steps_per_mm'],
        config['MotorController']['steps_per_degree']
    )

if SIMULATE:
    pna = PNASimulator()
else:
    pna = AgilentPNA(resource="GPIB0::16::INSTR", idQuery=True, reset=True)
pna.setMeasConfig(MeasConfig())
pna.setPowerConfig(PowerConfig())
