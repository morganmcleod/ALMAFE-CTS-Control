from CTSDevices.SpectrumAnalyzer.SpectrumAnalyzer import SpectrumAnalyzer, SpectrumAnalyzerSettings

settings = SpectrumAnalyzerSettings()
sa = SpectrumAnalyzer(resource="TCPIP0::10.1.1.10::inst0::INSTR")
ifStart = 4
ifStop = 12
ifStep = 0.1
settings.sweepPoints = int((ifStop - ifStart) / ifStep) + 1
sa.configureAll(settings)

success, msg = sa.configFreqStartStop(ifStart * 1e9, ifStop * 1e9)
print(success, msg)

success, msg = sa.configNarrowBand(6, 0.0001)
print(success, msg)

success, msg = sa.measureNarrowBand()
print(success, msg)
