
import app_Common.MeasurementStatus
import app_CTS.measProcedure.DataDisplay
import measProcedure.MixerTests
import hardware.ReferenceSources
import hardware.FEMC
import hardware.PowerDetect
import hardware.IFSystem
from Control.IFSystem.Interface import InputSelect, OutputSelect
from database.CTSDB import CTSDB
from Measure.MixerTests.MixerTestActions import MixerTestActions
from Measure.Shared.makeSteps import makeSteps
from DBBand6Cart.schemas.DUT_Type import DUT_Type

settingsContainer = measProcedure.MixerTests.settingsContainer
measurementStatus = app_Common.MeasurementStatus.measurementStatus()
receiver = hardware.FEMC.cartAssembly
ifSystem = hardware.IFSystem.ifSystem
ifPowerImpl = hardware.PowerDetect.ifPowerImpl
powerDetect = ifPowerImpl.powerDetect
dataDisplay = app_CTS.measProcedure.DataDisplay.dataDisplay

actor = MixerTestActions(
    hardware.ReferenceSources.loReference,
    hardware.FEMC.cartAssembly,
    measurementStatus,
    dataDisplay,
    DUT_Type.Band6_Cartridge
)