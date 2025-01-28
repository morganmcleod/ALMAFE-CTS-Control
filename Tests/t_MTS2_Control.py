from app_Common.CTSDB import CTSDB
from Measure.Shared.SelectSIS import SelectSIS
from Measure.Shared.SelectLNA import SelectLNA
from DBBand6Cart.PreampParams import PreampParam, PreampParams
from DBBand6Cart.MixerConfigs import MixerConfig, MixerConfigs, MixerKeys
from DBBand6Cart.MixerParams import MixerParam, MixerParams

import app_MTS2.hardware.MixerAssembly
import app_MTS2.hardware.IFSystem
import app_MTS2.hardware.NoiseTemperature
import app_MTS2.hardware.PowerDetect
import app_MTS2.hardware.RFSource
import app_MTS2.measProcedure.NoiseTemperature

ifSystem = app_MTS2.hardware.IFSystem.ifSystem
powerDetect = app_MTS2.hardware.PowerDetect.powerDetect
powerDetect.configure(config = app_MTS2.measProcedure.NoiseTemperature.settingsContainer.irSpecAnSettings)

# logging:
import logging
LOG_TO_FILE = True
LOG_FILE = 'ALMAFE-MTS2.log'
LOG_LEVEL = logging.INFO

logger = logging.getLogger("ALMAFE-CTS-Control")
logger.setLevel(LOG_LEVEL)
if LOG_TO_FILE:
    handler = logging.FileHandler(LOG_FILE)
else:
    handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(fmt = '%(asctime)s %(levelname)s:%(message)s'))
logger.addHandler(handler)

logger2 = logging.getLogger("ALMAFE-AMBDeviceLibrary")
logger2.setLevel(LOG_LEVEL)
logger2.addHandler(handler)

logger3 = logging.getLogger("ALMAFE-Instr")
logger3.setLevel(LOG_LEVEL)
logger3.addHandler(handler)

db = MixerConfigs(driver = CTSDB())
config: MixerConfig = db.read(serialNum = "3002")[0]
keys: MixerKeys = db.readKeys(config.key)

mixerAssembly = app_MTS2.hardware.MixerAssembly.mixerAssembly
mixerAssembly.setConfig(config.key)
mixerAssembly.loControl.setFrequency(221)
mixerAssembly.setBias(221)
# mixerAssembly.autoLOPower(50)
# mixerAssembly.autoLOPower(60)
mixerAssembly.autoLOPower()

rfSource = app_MTS2.hardware.RFSource.rfSource
rfSource.lockRF(231)
ifSystem.frequency = 10
rfSource.autoRFPower(powerDetect, -40)
rfSource.autoRFPower(powerDetect, -45)
rfSource.autoRFPower(powerDetect, -35)
print("\nLNA bias monitors:\n", 
    mixerAssembly.lnaBias.read_bias(SelectLNA.LNA1),
    "\n",
    mixerAssembly.lnaBias.read_bias(SelectLNA.LNA2)
)
print("\nSIS bias monitors:\n", 
    mixerAssembly.sisBias.read_bias(SelectSIS.SIS1),
    "\n",
    mixerAssembly.sisBias.read_bias(SelectSIS.SIS2)
)
print("\nSIS magnet current:\n", mixerAssembly.sisMagnet.readCurrent())
