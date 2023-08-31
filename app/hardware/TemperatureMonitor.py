from CTSDevices.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from CTSDevices.TemperatureMonitor.Simulator import TemperatureMonitorSimulator
from DebugOptions import *

if SIMULATE:
    temperatureMonitor = TemperatureMonitorSimulator()
else:
    temperatureMonitor = TemperatureMonitor("GPIB0::12::INSTR")

