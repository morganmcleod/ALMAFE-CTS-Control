from DebugOptions import *

POWER_DETECT_B6V2 = True
if POWER_DETECT_B6V2:
    from INSTR.SpectrumAnalyzer.SpectrumAnalyzer import SpectrumAnalyzer
    from INSTR.SpectrumAnalyzer.Simulator import SpectrumAnalyzerSimulator
    from Control.PowerDetect.PDSpecAn import PDSpecAn
    if SIMULATE:
        spectrumAnalyzer = SpectrumAnalyzerSimulator()
    else:
        spectrumAnalyzer = SpectrumAnalyzer("TCPIP0::10.1.1.10::inst0::INSTR")
    powerDetect = PDSpecAn(spectrumAnalyzer)


else:
    from INSTR.PowerMeter.KeysightE441X import PowerMeter
    from INSTR.PowerMeter.Simulator import PowerMeterSimulator
    from Control.PowerDetect.PDPowerMeter import PDPowerMeter
    if SIMULATE:
        powerMeter = PowerMeterSimulator()
    else:
        powerMeter = PowerMeter("GPIB0::13::INSTR")
    powerDetect = PDPowerMeter(powerMeter)

