import configparser
from DebugOptions import *
from AMB.FEMCDevice import FEMCDevice
from Controllers.RFSource.MTS2 import SidebandSource
import app_MTS2.hardware.ReferenceSources
import app_MTS2.hardware.MixerAssembly

NODE_ADDR = 0x13
RF_SOURCE_PORT = FEMCDevice.PORT_BAND7
conn = app_MTS2.hardware.MixerAssembly.conn

# load the rf source polarization channel to use from config:
config = configparser.ConfigParser()
config.read('ALMAFE-CTS-Control.ini')
try:
    paPol = int(config['RFSourceDevice']['RF_SOURCE_PA_POL'])
except:
    paPol = 0

rfSource = SidebandSource(
    conn,
    app_MTS2.hardware.ReferenceSources.rfReference,    
    nodeAddr = NODE_ADDR, 
    femcPort = RF_SOURCE_PORT, 
    polarization = paPol
)
rfSource.loDevice.setBandPower(RF_SOURCE_PORT, True)
