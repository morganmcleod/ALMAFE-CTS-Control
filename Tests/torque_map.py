import os
import sys
from pathlib import Path

# add the top-level project path to PYTHONPATH:
thisPath = Path.cwd()
projectRoot = str(thisPath.parent)
pythonRoot = str(thisPath.parent.parent)
sys.path.append(projectRoot)

# for deployment, add path to database and beam eff library:
sys.path.append(pythonRoot + '/ALMAFE-CTS-Database')
sys.path.append(pythonRoot + '/beam-efficiency-python')

# and change to that directory:
os.chdir(projectRoot)

from INSTR.MotorControl.GalilDMCSocket import MotorController
from INSTR.MotorControl.schemas import *

# Commands to test
# TT: Tell torque
# AG: Set Amplifier Gain
# TL: Torque Limit
# TK: Peak Torque Limit