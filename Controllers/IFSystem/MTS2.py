from .Interface import IFSystem_Interface, InputSelect, OutputSelect, DeviceInfo
from INSTR.InputSwitch.MTS2 import InputSwitch_MTS2
from INSTR.SpectrumAnalyzer.SpectrumAnalyzer import SpectrumAnalyzer, SpectrumAnalyzerSettings
from DebugOptions import *

class IFSystem(IFSystem_Interface):

    def __init__(self, 
            inputSwitch: InputSwitch_MTS2, 
            spectrumAnalyzer: SpectrumAnalyzer):
        self.inputSwitch = inputSwitch
        self.spectrumAnalyzer = spectrumAnalyzer
        self.reset()

    def reset(self) -> None:
        self.inputSwitch.selected = InputSelect.POL0_USB
        self._output_select = OutputSelect.POWER_DETECT
        self.freqCenter = 0
        self.freqSpan = 0.0001
        self.spectrumAnalyzer.configureAll(SpectrumAnalyzerSettings())
        self.spectrumAnalyzer.configFreqStartStop(2.0e9, 22.0e9)

    @property
    def device_info(self) -> DeviceInfo:
        switchOk = self.inputSwitch.connected()
        specAnOk = self.spectrumAnalyzer.connected()
        reason = ""
        if not switchOk:
            reason += "Input switch not connected. "
        if not specAnOk:
            reason += "Spectrum analyzer not connected. "
        if SIMULATE:
            return DeviceInfo(
                name = 'IF system MTS2',
                resource = 'Simulated input switch and spectrum analyzer',
                connected = True,
                reason = reason
            )
        else: 
            return DeviceInfo(
                name = "IF System MTS2",
                resource = "Input switch and spectrum analyzer",
                connected = switchOk and specAnOk,
                reason = reason
            )

    @property
    def input_select(self) -> InputSelect:
        return self.inputSwitch.selected
    
    @input_select.setter
    def input_select(self, inputSelect: InputSelect):
        self.inputSwitch.selected = inputSelect
        
    def set_pol_sideband(self, pol: int = 0, sideband: int | str = 'USB') -> None:
        self.inputSwitch.select_pol_sideband(pol, sideband)

    @property
    def output_select(self) -> OutputSelect:
        return self._output_select
    
    @output_select.setter
    def output_select(self, outputSelect: OutputSelect):
        self._output_select = outputSelect
    
    @property
    def frequency(self) -> float:
        return self.freqCenter
    
    @frequency.setter
    def frequency(self, freq_GHz: float):
        self.freqCenter = freq_GHz
        if self.freqCenter > 0:
            self.spectrumAnalyzer.configNarrowBand(self.freqCenter, self.freqSpan)
        else:
            self.spectrumAnalyzer.endNarrowBand()

    @property
    def bandwidth(self) -> float:
        return self.freqSpan
    
    @bandwidth.setter
    def bandwidth(self, bw_GHz: float):
        self.freqSpan = bw_GHz
        if self.freqCenter > 0:
            self.spectrumAnalyzer.configWideBand(self.freqCenter, self.freqSpan)
        else:
            self.spectrumAnalyzer.endNarrowBand()

    @property
    def attenuation(self) -> float:
        return 0

    @attenuation.setter
    def attenuation(self, atten_dB: float):
        pass
   