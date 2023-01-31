from CTSDevices.SignalGenerator.Keysight_PSG_MXG import SignalGenerator

loReference = SignalGenerator("GPIB0::19::INSTR", reset = False)
rfReference = SignalGenerator("GPIB0::17::INSTR", reset = False)