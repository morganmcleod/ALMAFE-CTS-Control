import configparser
from DebugOptions import *

config = configparser.ConfigParser()
config.read('ALMAFE-CTS-Control.ini')
try:
    IF_SYSTEM_B6V2 = config['IFSystem']['IFSystem'] == 'B6V2'
except:
    IF_SYSTEM_B6V2 = False

if IF_SYSTEM_B6V2:
    # IF system temporary B6v2
    import hardware.PowerDetect
    from Control.IFSystem.TemporaryB6v2 import IFSystem
    from INSTR.InputSwitch.ExternalSwitch import ExternalSwitch
    externalSwitch = ExternalSwitch("GPIB0::29::INSTR", SIMULATE)
    ifSystem = IFSystem(externalSwitch, hardware.PowerDetect.spectrumAnalyzer)

else:
    # Warm IF plate
    from INSTR.WarmIFPlate.Attenuator import Attenuator
    from INSTR.InputSwitch.InputSwitch import InputSwitch
    from INSTR.WarmIFPlate.OutputSwitch import OutputSwitch
    from INSTR.WarmIFPlate.YIGFilter import YIGFilter
    from INSTR.WarmIFPlate.WarmIFPlate import WarmIFPlate
    from Control.IFSystem.WarmIFPlate import IFSystem
    import hardware.NoiseTemperature
    
    warmIFPlate = WarmIFPlate(
        Attenuator(resource = "GPIB0::28::INSTR", simulate = SIMULATE),
        InputSwitch(resource = "GPIB0::9::INSTR", simulate = SIMULATE),
        hardware.NoiseTemperature.powerSupply,
        OutputSwitch(resource = "GPIB0::9::INSTR", simulate = SIMULATE),
        YIGFilter(resource = "GPIB0::9::INSTR", simulate = SIMULATE)
    )
    ifSystem = IFSystem(warmIFPlate)



