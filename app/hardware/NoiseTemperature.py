from hardware.ReferenceSources import loReference, rfReference
from hardware.FEMC import cartAssembly, rfSrcDevice
from hardware.WarmIFPlate import warmIFPlate
from CTSDevices.PowerMeter.KeysightE441X import PowerMeter
from CTSDevices.PowerMeter.Simulator import PowerMeterSimulator
from CTSDevices.PowerSupply.AgilentE363xA import PowerSupply
from CTSDevices.PowerSupply.Simulator import PowerSupplySimulator
from CTSDevices.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from CTSDevices.TemperatureMonitor.Simulator import TemperatureMonitorSimulator
from CTSDevices.Chopper.Band6Chopper import Chopper
from .WarmIFPlate import warmIFPlate
from DebugOptions import *
from Measure.NoiseTemperature.NoiseTemperature import NoiseTemperature

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

chopper = Chopper()

noiseTemperature = NoiseTemperature(
    loReference, 
    rfReference,
    cartAssembly,
    rfSrcDevice,
    warmIFPlate, 
    powerMeter,
    powerSupply,
    temperatureMonitor,
    chopper
)
