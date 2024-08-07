from app.measProcedure.MeasurementStatus import measurementStatus
from app.measProcedure.DataDisplay import dataDisplay
from app.measProcedure.NoiseTemperature import settingsContainer as settings
from app.database.CTSDB import CTSDB
from hardware.ReferenceSources import loReference, rfReference
from hardware.FEMC import cartAssembly as receiver, rfSrcDevice
from hardware.NoiseTemperature import powerSupply, temperatureMonitor, chopper, coldLoad
from hardware.PowerDetect import powerDetect
from hardware.IFSystem import ifSystem
from Measure.NoiseTemperature.NoiseTempActions import NoiseTempActions
from Measure.Shared.makeSteps import makeSteps
from DBBand6Cart.schemas.DUT_Type import DUT_Type
from DBBand6Cart.NoiseTempRawData import NoiseTempRawData
from DBBand6Cart.WarmIFNoiseData import WarmIFNoiseData

actor = NoiseTempActions(
    loReference,
    rfReference,
    receiver,
    rfSrcDevice,
    ifSystem,
    powerDetect, 
    temperatureMonitor,
    powerSupply, 
    coldLoad,
    chopper, 
    measurementStatus,
    dataDisplay,
    DUT_Type.Band6_Cartridge,
    settings
)