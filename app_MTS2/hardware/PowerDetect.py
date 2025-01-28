import configparser
from DebugOptions import *
from Control.PowerDetect.IFPowerImpl import IFPowerImpl
from Control.PowerDetect.PDPowerMeter import PDPowerMeter
from INSTR.SpectrumAnalyzer.Simulator import SpectrumAnalyzerSimulator
from INSTR.PowerMeter.KeysightE441X import PowerMeter
from INSTR.PowerMeter.Simulator import PowerMeterSimulator

# load power detect setting
config = configparser.ConfigParser()
config.read('ALMAFE-CTS-Control.ini')
try:
    POWER_DETECT_B6V2 = config['PowerDetect']['PowerDetect'] == 'B6V2'
except:
    POWER_DETECT_B6V2 = False

if POWER_DETECT_B6V2:
    # B6v2 powerDetect is spectrrum analyzer
    from INSTR.SpectrumAnalyzer.SpectrumAnalyzer import SpectrumAnalyzer    
    from Control.PowerDetect.PDSpecAn import PDSpecAn
    if SIMULATE:
        spectrumAnalyzer = SpectrumAnalyzerSimulator()
    else:
        spectrumAnalyzer = SpectrumAnalyzer("TCPIP0::10.1.1.10::inst0::INSTR")
    powerDetect = PDSpecAn(spectrumAnalyzer)

else:    
    # MTS1 powerDetect is power meter
    from INSTR.PowerMeter.Simulator import PowerMeterSimulator
    spectrumAnalyzer = SpectrumAnalyzerSimulator()
    if SIMULATE:
        powerMeter = PowerMeterSimulator()
    else:
        powerMeter = PowerMeter("GPIB0::13::INSTR")
    powerDetect = PDPowerMeter(powerMeter)

# instantiate the interface required by CCADevice for power detection during I-V curves:
ifPowerImpl = IFPowerImpl(powerDetect)
