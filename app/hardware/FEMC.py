from AMB.AMBConnectionDLL import AMBConnectionDLL
from AMB.FEMCDevice import FEMCDevice
from AMB.LODevice import LODevice
from AMB.CCADevice import CCADevice
from CTSDevices.Cartridge.CartAssembly import CartAssembly
import configparser

CARTRIDGE_BAND = 6
RF_SOURCE_PORT = 7
RF_SOURCE_PA_POL = 0

config = configparser.ConfigParser()
config.read('FrontEndAMBDLL.ini')
dllName = config['load']['dll']
conn = AMBConnectionDLL(channel = 0, dllName = dllName)

ccaDevice = CCADevice(conn, nodeAddr = 0x13, band = CARTRIDGE_BAND)
ccaDevice.initSession()
ccaDevice.setBandPower(CARTRIDGE_BAND, True)

loDevice = LODevice(conn, nodeAddr = 0x13, band = CARTRIDGE_BAND)
loDevice.initSession()
loDevice.setBandPower(CARTRIDGE_BAND, True)
loDevice.setYTOLimits(12.22, 14.77)

cartAssembly = CartAssembly(ccaDevice, loDevice)

rfSrcDevice = LODevice(conn, nodeAddr = 0x13, band = CARTRIDGE_BAND, femcPort = RF_SOURCE_PORT)
rfSrcDevice.initSession()
rfSrcDevice.setBandPower(RF_SOURCE_PORT, True)
rfSrcDevice.setYTOLimits(11.6, 15.43)
rfSrcDevice.paPol = RF_SOURCE_PA_POL

