from DebugOptions import *
from AMB.AMBConnectionNixnet import AMBConnectionNixnet
from AMB.FEMCDevice import FEMCDevice
from INSTR.CurrentSource.Keithley24XX import CurrentSource
from Controllers.LO.MTS2 import LOControl
from Controllers.LNA.MTS2 import LNABias
from Controllers.SIS.MTS import SISBias
from Controllers.Magnet.MTS2 import SISMagnet
from Controllers.Receiver.MixerAssembly import MixerAssembly
import app_MTS2.hardware.ReferenceSources
import app_MTS2.hardware.NoiseTemperature

NODE_ADDR = 0x13
CARTRIDGE_BAND = FEMCDevice.PORT_BAND6
LNA_CONTROL_PORT = FEMCDevice.PORT_BAND3

# import configparser
# config = configparser.ConfigParser()
# config.read('FrontEndAMBDLL.ini')
# dllName = config['load']['dll']
conn = AMBConnectionNixnet(channel = 1)

femcDevice = FEMCDevice(conn, NODE_ADDR)
# set FE_MODE depending on debug options:
femcDevice.setFeMode(FEMCDevice.MODE_SIMULATE if SIMULATE else FEMCDevice.MODE_TROUBLESHOOTING)

loControl = LOControl(
    conn,
    app_MTS2.hardware.ReferenceSources.loReference,
    nodeAddr = NODE_ADDR, 
    band = CARTRIDGE_BAND
)
loControl.loDevice.setBandPower(CARTRIDGE_BAND, True)

lnaBias = LNABias(
    conn, 
    nodeAddr = NODE_ADDR, 
    femcPort = LNA_CONTROL_PORT
)
lnaBias.ccaDevice.setBandPower(LNA_CONTROL_PORT, True)

sisBias = SISBias(simulate = SIMULATE)

currentSource = CurrentSource("GPIB0::25::INSTR")

sisMagnet = SISMagnet(currentSource, simulate = SIMULATE)

mixerAssembly = MixerAssembly(
    sisBias,
    sisMagnet,
    loControl,
    lnaBias,
    app_MTS2.hardware.NoiseTemperature.temperatureMonitor
)
