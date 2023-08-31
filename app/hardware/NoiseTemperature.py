from hardware.ReferenceSources import loReference, rfReference
from hardware.FEMC import cartAssembly, rfSrcDevice
from CTSDevices.PowerMeter.KeysightE441X import PowerMeter
from CTSDevices.PowerMeter.Simulator import PowerMeterSimulator
from CTSDevices.PowerSupply.AgilentE363xA import PowerSupply
from CTSDevices.PowerSupply.Simulator import PowerSupplySimulator
from CTSDevices.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from CTSDevices.TemperatureMonitor.Simulator import TemperatureMonitorSimulator
from .WarmIFPlate import warmIFPlate
from DebugOptions import *
from Measure.NoiseTemperature.WarmIFNoise import MeasureWarmIFNoise

if SIMULATE:
    temperatureMonitor = TemperatureMonitorSimulator()
else:
    temperatureMonitor = TemperatureMonitor("GPIB0::12::INSTR")

if SIMULATE:
    powerMeter = PowerMeterSimulator()
else:
    powerMeter = PowerMeter("GPIB0::13::INSTR")

if SIMULATE:
    powerSupply = PowerSupplySimulator()
else:
    powerSupply = PowerSupply("GPIB0::5::INSTR")


warmIFNoise = MeasureWarmIFNoise(
    warmIFPlate = warmIFPlate, 
    powerMeter = powerMeter,
    powerSupply = powerSupply,
    temperatureMonitor = temperatureMonitor
)
