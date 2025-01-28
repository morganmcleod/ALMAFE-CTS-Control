import configparser
from DebugOptions import *
from AMB.AMBConnectionDLL import AMBConnectionDLL
from AMB.FEMCDevice import FEMCDevice
from Control.MTS_LOControl.MTS2 import LOControl
from Control.MTS_RFSource.MTS2 import SidebandSource
from Control.MTS_LNABias.MTS2 import LNABias

NODE_ADDR = 0x13
CARTRIDGE_BAND = FEMCDevice.PORT_BAND6
RF_SOURCE_PORT = FEMCDevice.PORT_BAND7
LNA_CONTROL_PORT = FEMCDevice.PORT_BAND3

config = configparser.ConfigParser()
config.read('FrontEndAMBDLL.ini')
dllName = config['load']['dll']
conn = AMBConnectionDLL(channel = 0, dllName = dllName)

# set FE_MODE depending on debug options:
feMode = FEMCDevice.MODE_SIMULATE if SIMULATE else FEMCDevice.MODE_TROUBLESHOOTING 

# load the rf source polarization channel to use from config:
config = configparser.ConfigParser()
config.read('ALMAFE-CTS-Control.ini')
try:
    paPol = int(config['RFSourceDevice']['RF_SOURCE_PA_POL'])
except:
    paPol = 0

loControl = LOControl(conn, nodeAddr = NODE_ADDR, femcPort = CARTRIDGE_BAND)
loControl.loDevice.setFeMode(feMode)
loControl.loDevice.setBandPower(CARTRIDGE_BAND, True)
loControl.loDevice.setYTOLimits(12.22, 14.77)

rfSource = SidebandSource(conn, nodeAddr = NODE_ADDR, femcPort = RF_SOURCE_PORT, polarization = paPol)
rfSource.loDevice.setFeMode(feMode)
rfSource.loDevice.setBandPower(RF_SOURCE_PORT, True)
rfSource.loDevice.setYTOLimits(12.22, 14.77)

lnaBias = LNABias(conn, nodeAddr = NODE_ADDR, femcPort = LNA_CONTROL_PORT)
lnaBias.ccaDevice.setBandPower(LNA_CONTROL_PORT, True)
lnaBias.ccaDevice.setFeMode(feMode)

femcDevice = FEMCDevice(conn, NODE_ADDR)