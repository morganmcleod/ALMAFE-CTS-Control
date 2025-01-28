
import app_Common.measProcedure.MeasurementStatus
import app_Common.measProcedure.DataDisplay
import app_CTS.measProcedure.MixerTests
import hardware.ReferenceSources
import hardware.FEMC
import hardware.PowerDetect
import hardware.IFSystem
from Controllers.IFSystem.Interface import InputSelect, OutputSelect
from database.CTSDB import CTSDB
from Measure.MixerTests.MixerTestActions import MixerTestActions
from Measure.Shared.makeSteps import makeSteps
from DBBand6Cart.schemas.DUT_Type import DUT_Type

settingsContainer = app_CTS.measProcedure.MixerTests.settingsContainer
measurementStatus = app_Common.measProcedure.MeasurementStatus.measurementStatus()
receiver = hardware.FEMC.cartAssembly
ifSystem = hardware.IFSystem.ifSystem
ifPowerImpl = hardware.PowerDetect.ifPowerImpl
powerDetect = ifPowerImpl.powerDetect
dataDisplay = app_Common.measProcedure.DataDisplay.dataDisplay

actor = MixerTestActions(
    DUT_Type.Band6_Cartridge,    
    hardware.FEMC.cartAssembly,
    measurementStatus,
    dataDisplay
)