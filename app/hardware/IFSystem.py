from DebugOptions import *
IF_SYSTEM_B6V2 = True


if IF_SYSTEM_B6V2:
    # IF system temporary B6v2
    from hardware.PowerDetect import spectrumAnalyzer
    from Control.IFSystem.TemporaryB6v2 import IFSystem
    from INSTR.InputSwitch.ExternalSwitch import ExternalSwitch
    externalSwitch = ExternalSwitch("GPIB0::29::INSTR", SIMULATE)
    ifSystem = IFSystem(externalSwitch, spectrumAnalyzer)

else:
    # Warm IF plate
    from INSTR.WarmIFPlate.Attenuator import Attenuator
    from INSTR.InputSwitch.InputSwitch import InputSwitch
    from INSTR.WarmIFPlate.NoiseSource import NoiseSource
    from INSTR.WarmIFPlate.OutputSwitch import OutputSwitch
    from INSTR.WarmIFPlate.YIGFilter import YIGFilter
    from INSTR.WarmIFPlate.WarmIFPlate import WarmIFPlate
    from Control.IFSystem.WarmIfPlate import IFSystem
    
    warmIFPlate = WarmIFPlate(
        Attenuator(resource = "GPIB0::28::INSTR", simulate = SIMULATE),
        InputSwitch(resource = "GPIB0::9::INSTR", simulate = SIMULATE),
        NoiseSource(resource = "GPIB0::5::INSTR", simulate = SIMULATE),
        OutputSwitch(resource = "GPIB0::9::INSTR", simulate = SIMULATE),
        YIGFilter(resource = "GPIB0::9::INSTR", simulate = SIMULATE)
    )
    ifSystem = IFSystem(warmIFPlate)



