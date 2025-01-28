from INSTR.PowerSupply.AgilentE363xA import PowerSupply
from INSTR.PowerSupply.Simulator import PowerSupplySimulator
from INSTR.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from INSTR.TemperatureMonitor.Simulator import TemperatureMonitorSimulator
from INSTR.ColdLoad.AMI1720 import AMI1720
from INSTR.ColdLoad.AMI1720Simulator import AMI1720Simulator
from INSTR.Chopper.FETMSChopper import Chopper
from DebugOptions import *

if SIMULATE:
    temperatureMonitor = TemperatureMonitorSimulator()
else:
    temperatureMonitor = TemperatureMonitor("GPIB0::12::INSTR")

if SIMULATE:
    powerSupply = PowerSupplySimulator()
else:
    powerSupply = PowerSupply("GPIB0::5::INSTR")

if SIMULATE:
    coldLoad = AMI1720Simulator()
else:
    coldLoad = AMI1720("TCPIP0::10.1.1.5::7180::SOCKET")

chopper = Chopper(simulate = SIMULATE)

