import app.measProcedure.MeasurementStatus
import measProcedure.DataDisplay
import measProcedure.NoiseTemperature
import hardware.ReferenceSources
import hardware.FEMC
import hardware.NoiseTemperature
import hardware.PowerDetect
import hardware.IFSystem
import hardware.BeamScanner
from database.CTSDB import CTSDB
from Measure.BeamScanner.schemas import Position
from Measure.NoiseTemperature.NoiseTempActions import NoiseTempActions
from Measure.Shared.makeSteps import makeSteps
from Measure.Shared.SelectPolarization import SelectPolarization
from DBBand6Cart.schemas.DUT_Type import DUT_Type
from DBBand6Cart.NoiseTempRawData import NoiseTempRawData
from DBBand6Cart.WarmIFNoiseData import WarmIFNoiseData
from Control.PowerDetect.Interface import DetectMode

settingsContainer = measProcedure.NoiseTemperature.settingsContainer
measurementStatus = app.measProcedure.MeasurementStatus.measurementStatus()
receiver = hardware.FEMC.cartAssembly
ifSystem = hardware.IFSystem.ifSystem
powerDetect = hardware.PowerDetect.powerDetect
pdPowerMeter = hardware.PowerDetect.pdPowerMeter
coldLoad = hardware.NoiseTemperature.coldLoad
beamScanMotorController = hardware.BeamScanner.motorController

actor = NoiseTempActions(
    hardware.ReferenceSources.loReference,
    hardware.ReferenceSources.rfReference,
    hardware.FEMC.cartAssembly,
    hardware.FEMC.rfSrcDevice,
    hardware.IFSystem.ifSystem,
    hardware.PowerDetect.powerDetect, 
    hardware.NoiseTemperature.temperatureMonitor,
    hardware.NoiseTemperature.powerSupply, 
    hardware.NoiseTemperature.coldLoad,
    hardware.NoiseTemperature.chopper, 
    measurementStatus,
    measProcedure.DataDisplay.dataDisplay,
    DUT_Type.Band6_Cartridge,
    settingsContainer
)