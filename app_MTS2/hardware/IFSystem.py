import configparser
from DebugOptions import *

config = configparser.ConfigParser()
config.read('ALMAFE-CTS-Control.ini')
try:
    IF_SYSTEM_B6V2 = config['IFSystem']['IFSystem'] == 'B6V2'
except:
    IF_SYSTEM_B6V2 = False

if IF_SYSTEM_B6V2:
    # IF system MTS-2
    import app_MTS2.hardware.PowerDetect
    from INSTR.InputSwitch.MTS2 import InputSwitch_MTS2
    from Controllers.IFSystem.MTS2 import IFSystem
    inputSwitch = InputSwitch_MTS2(simulate = SIMULATE)
    ifSystem = IFSystem(inputSwitch, app_MTS2.hardware.PowerDetect.spectrumAnalyzer)

else:
    # Warm IF plate
    from INSTR.WarmIFPlate.Attenuator import Attenuator
    from INSTR.InputSwitch.InputSwitch import InputSwitch
    from INSTR.WarmIFPlate.OutputSwitch import OutputSwitch
    from INSTR.WarmIFPlate.YIGFilter import YIGFilter
    from INSTR.WarmIFPlate.WarmIFPlate import WarmIFPlate
    from Controllers.IFSystem.WarmIFPlate import IFSystem
    import hardware.NoiseTemperature
    
    warmIFPlate = WarmIFPlate(
        Attenuator(resource = "GPIB0::28::INSTR", simulate = SIMULATE),
        InputSwitch(resource = "GPIB0::9::INSTR", simulate = SIMULATE),
        hardware.NoiseTemperature.powerSupply,
        OutputSwitch(resource = "GPIB0::9::INSTR", simulate = SIMULATE),
        YIGFilter(resource = "GPIB0::9::INSTR", simulate = SIMULATE)
    )
    ifSystem = IFSystem(warmIFPlate)



