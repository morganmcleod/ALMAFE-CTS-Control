from AMB.AMBConnectionDLL import AMBConnectionDLL
from AMB.FEMCDevice import FEMCDevice
from AMB.LODevice import LODevice
from AMB.CCADevice import CCADevice
from AMB.FEMCDevice import FEMCDevice
from Controllers.Receiver.CartAssembly import CartAssembly
from Controllers.RFSource.CTS import RFSource
import configparser
from DebugOptions import *

CARTRIDGE_BAND = 6
RF_SOURCE_PORT = 7
NODE_ADDR = 0x13

config = configparser.ConfigParser()
config.read('FrontEndAMBDLL.ini')
dllName = config['load']['dll']
conn = AMBConnectionDLL(channel = 0, dllName = dllName)

# set FE_MODE depending on debug options:
feMode = FEMCDevice.MODE_SIMULATE if SIMULATE else FEMCDevice.MODE_TROUBLESHOOTING 

femcDevice = FEMCDevice(conn, NODE_ADDR)

ccaDevice = CCADevice(conn, nodeAddr = NODE_ADDR, band = CARTRIDGE_BAND)
ccaDevice.setFeMode(feMode)
ccaDevice.setBandPower(CARTRIDGE_BAND, True)

loDevice = LODevice(conn, nodeAddr = NODE_ADDR, band = CARTRIDGE_BAND)
ccaDevice.setFeMode(feMode)
loDevice.setBandPower(CARTRIDGE_BAND, True)

cartAssembly = CartAssembly(ccaDevice, loDevice)

# load the rf source polarization channel to use from config:
config = configparser.ConfigParser()
config.read('ALMAFE-CTS-Control.ini')
try:
    paPol = int(config['RFSourceDevice']['RF_SOURCE_PA_POL'])
except:
    paPol = 0
rfSrcDevice = RFSource(conn, nodeAddr = NODE_ADDR, band = CARTRIDGE_BAND, femcPort = RF_SOURCE_PORT, paPol = paPol)
ccaDevice.setFeMode(feMode)
rfSrcDevice.setBandPower(RF_SOURCE_PORT, True)
