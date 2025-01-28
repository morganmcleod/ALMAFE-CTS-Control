import logging

# imports of classes and functions, for use by the script
from app_Common.CTSDB import CTSDB
from Measure.Shared.makeSteps import makeSteps
from Measure.Shared.SelectPolarization import SelectPolarization
from DBBand6Cart.schemas.DUT_Type import DUT_Type
from DBBand6Cart.schemas.MixerTest import MixerTest
from DBBand6Cart.NoiseTempRawData import NoiseTempRawData
from DBBand6Cart.schemas.NoiseTempRawDatum import NoiseTempRawDatum, COLUMNS as NT_COLUMNS
from DBBand6Cart.WarmIFNoiseData import WarmIFNoiseData
from DBBand6Cart.MixerConfigs import MixerConfigs, MixerConfig, MixerKeys
from DBBand6Cart.MixerParams import MixerParams, MixerParam
from Controllers.PowerDetect.Interface import DetectMode
from Measure.Shared.SelectSIS import SelectSIS
from Measure.NoiseTemperature.schemas import BiasOptResult
from INSTR.InputSwitch.Interface import InputSelect

# imports of singleton objects:
import app_MTS2.hardware.RFSource
import app_MTS2.hardware.ReferenceSources
import app_MTS2.hardware.MixerAssembly
import app_MTS2.hardware.NoiseTemperature
import app_MTS2.hardware.PowerDetect
import app_MTS2.hardware.IFSystem
import app_Common.measProcedure.MeasurementStatus
import app_Common.measProcedure.DataDisplay
import app_MTS2.measProcedure.NoiseTemperature

# short names for singleton objects, for use by the script:
settingsContainer = app_MTS2.measProcedure.NoiseTemperature.settingsContainer
measurementStatus = app_Common.measProcedure.MeasurementStatus.measurementStatus()
dataDisplay = app_Common.measProcedure.DataDisplay.dataDisplay
receiver = app_MTS2.hardware.MixerAssembly.mixerAssembly
ifSystem = app_MTS2.hardware.IFSystem.ifSystem
powerDetect = app_MTS2.hardware.PowerDetect.powerDetect
coldLoad = app_MTS2.hardware.NoiseTemperature.coldLoad
chopper = app_MTS2.hardware.NoiseTemperature.chopper
logger = logging.getLogger("ALMAFE-CTS-Control")

# reload all settings from files:
settingsContainer.loadSettings()
# MTS only measure pol0:
settingsContainer.noiseTempSettings.polarization = SelectPolarization.POL0.value

# imports for the actor:
from Measure.NoiseTemperature.NoiseTempActions import NoiseTempActions
from DBBand6Cart.schemas.DUT_Type import DUT_Type

# instantiate the singleton actor, for use by the script:
actor = NoiseTempActions(
    DUT_Type.Band6_MxrPreampAssys,
    app_MTS2.hardware.ReferenceSources.loReference,
    app_MTS2.hardware.ReferenceSources.rfReference,
    app_MTS2.hardware.MixerAssembly.mixerAssembly,
    app_MTS2.hardware.RFSource.rfSource,
    app_MTS2.hardware.IFSystem.ifSystem,
    app_MTS2.hardware.PowerDetect.powerDetect, 
    app_MTS2.hardware.NoiseTemperature.temperatureMonitor,
    None, # no PowerSupply for MTS-2 warm IF noise measurement.
    app_MTS2.hardware.NoiseTemperature.coldLoad,
    app_MTS2.hardware.NoiseTemperature.chopper, 
    app_Common.measProcedure.MeasurementStatus.measurementStatus(),
    app_Common.measProcedure.DataDisplay.dataDisplay,
    app_MTS2.measProcedure.NoiseTemperature.settingsContainer
)