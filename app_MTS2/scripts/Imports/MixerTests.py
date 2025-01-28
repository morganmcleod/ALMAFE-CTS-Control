import logging

# imports of classes and functions, for use by the script
from app_Common.CTSDB import CTSDB
from Measure.Shared.makeSteps import makeSteps
from Controllers.IFSystem.Interface import InputSelect, OutputSelect
from Measure.Shared.SelectSIS import SelectSIS
from Measure.Shared.SelectPolarization import SelectPolarization
from AMB.schemas.MixerTests import IVCurvePoint as AMB_IVCurvePoint
from DBBand6Cart.IVCurves import IVCurves, IVCurvePoint as DB_IVCurvePoint
from DBBand6Cart.MixerTests import MixerTest

# imports of singleton objects:
import app_MTS2.measProcedure.MixerTests
import app_MTS2.hardware.MixerAssembly
import app_MTS2.hardware.PowerDetect
import app_MTS2.hardware.IFSystem
import app_MTS2.hardware.NoiseTemperature
import app_Common.measProcedure.MeasurementStatus
import app_Common.measProcedure.DataDisplay

# short names for the singleton objects, for use by the script:
settingsContainer = app_MTS2.measProcedure.MixerTests.settingsContainer
measurementStatus = app_Common.measProcedure.MeasurementStatus.measurementStatus()
dataDisplay = app_Common.measProcedure.DataDisplay.dataDisplay
receiver = app_MTS2.hardware.MixerAssembly.mixerAssembly
ifSystem = app_MTS2.hardware.IFSystem.ifSystem
ifPowerImpl = app_MTS2.hardware.PowerDetect.ifPowerImpl
powerDetect = app_MTS2.hardware.PowerDetect.powerDetect
tempMonitor = app_MTS2.hardware.NoiseTemperature.temperatureMonitor
chopper = app_MTS2.hardware.NoiseTemperature.chopper
logger = logging.getLogger("ALMAFE-CTS-Control")

# imports for the actor:
from Measure.MixerTests.MixerTestActions import MixerTestActions
from DBBand6Cart.schemas.DUT_Type import DUT_Type

# instantiate the singleton actor, for use by the script:
actor = MixerTestActions(
    DUT_Type.Band6_MxrPreampAssys,
    app_MTS2.hardware.MixerAssembly.mixerAssembly,
    app_MTS2.hardware.IFSystem.ifSystem,
    app_MTS2.hardware.NoiseTemperature.temperatureMonitor,
    app_MTS2.hardware.NoiseTemperature.chopper,
    app_Common.measProcedure.MeasurementStatus.measurementStatus(),
    app_Common.measProcedure.DataDisplay.dataDisplay
)