from AMB.AMBConnectionDLL import AMBConnectionDLL
from AMB.FEMCDevice import FEMCDevice
from AMB.LODevice import LODevice
from AMB.CCADevice import CCADevice

CARTRIDGE_BAND = 6
RF_SOURCE_PORT = 7

conn = AMBConnectionDLL()

ccaDevice = CCADevice(conn, nodeAddr = 0x13, band = CARTRIDGE_BAND)
ccaDevice.initSession(FEMCDevice.MODE_SIMULATE)
ccaDevice.setBandPower(CARTRIDGE_BAND, True)

loDevice = LODevice(conn, nodeAddr = 0x13, band = CARTRIDGE_BAND)
loDevice.initSession(FEMCDevice.MODE_SIMULATE)
loDevice.setBandPower(CARTRIDGE_BAND, True)
loDevice.setYTOLimits(12.22, 14.77)

srcDevice = LODevice(conn, nodeAddr = 0x13, band = CARTRIDGE_BAND, femcPort = RF_SOURCE_PORT)
srcDevice.initSession(FEMCDevice.MODE_SIMULATE)
srcDevice.setBandPower(RF_SOURCE_PORT, True)
