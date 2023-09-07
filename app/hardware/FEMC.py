from AMB.AMBConnectionDLL import AMBConnectionDLL
from AMB.FEMCDevice import FEMCDevice
from AMB.LODevice import LODevice
from AMB.CCADevice import CCADevice
from AMB.FEMCDevice import FEMCDevice
from CTSDevices.FEMC.CartAssembly import CartAssembly
from CTSDevices.FEMC.RFSource import RFSource
import configparser
from DebugOptions import *

CARTRIDGE_BAND = 6
RF_SOURCE_PORT = 7
RF_SOURCE_PA_POL = 0
NODE_ADDR = 0x13

config = configparser.ConfigParser()
config.read('FrontEndAMBDLL.ini')
dllName = config['load']['dll']
conn = AMBConnectionDLL(channel = 0, dllName = dllName)

# set FE_MODE depending on debug options:
feMode = FEMCDevice.MODE_SIMULATE if SIMULATE else FEMCDevice.MODE_TROUBLESHOOTING 

ccaDevice = CCADevice(conn, nodeAddr = NODE_ADDR, band = CARTRIDGE_BAND)
ccaDevice.setFeMode(feMode)
ccaDevice.setBandPower(CARTRIDGE_BAND, True)

loDevice = LODevice(conn, nodeAddr = NODE_ADDR, band = CARTRIDGE_BAND)
ccaDevice.setFeMode(feMode)
loDevice.setBandPower(CARTRIDGE_BAND, True)
loDevice.setYTOLimits(12.22, 14.77)

cartAssembly = CartAssembly(ccaDevice, loDevice)

rfSrcDevice = RFSource(conn, nodeAddr = NODE_ADDR, band = CARTRIDGE_BAND, femcPort = RF_SOURCE_PORT, paPol = RF_SOURCE_PA_POL)
ccaDevice.setFeMode(feMode)
rfSrcDevice.setBandPower(RF_SOURCE_PORT, True)
rfSrcDevice.setYTOLimits(11.6, 15.43)

femcDevice = FEMCDevice(conn, NODE_ADDR)