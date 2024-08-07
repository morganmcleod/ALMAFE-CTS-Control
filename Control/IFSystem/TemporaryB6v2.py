from .Interface import IFSystem_Interface, InputSelect, OutputSelect, DeviceInfo
from INSTR.InputSwitch.ExternalSwitch import ExternalSwitch
from INSTR.SpectrumAnalyzer.SpectrumAnalyzer import SpectrumAnalyzer
from DebugOptions import *

class IFSystem(IFSystem_Interface):

    def __init__(self, 
            externalSwitch: ExternalSwitch, 
            spectrumAnalyzer: SpectrumAnalyzer):
        self.externalSwitch = externalSwitch
        self.spectrumAnalyzer = spectrumAnalyzer
        self.reset()

    def reset(self) -> None:
        self.externalSwitch.selected = InputSelect.POL0_USB
        self._output_select = OutputSelect.POWER_DETECT
        self.freqCenter = 0
        self.freqSpan = 0.0001

    @property
    def device_info(self) -> DeviceInfo:
        if SIMULATE:
            return DeviceInfo(
                name = 'IF system',
                resource = 'simulated spectrum analyzer',
                connected = True
            )
            
        switchOk = self.externalSwitch.connected()
        specAnOk = self.spectrumAnalyzer.connected()
        reason = ""
        if not switchOk:
            reason += "External switch not connected. "
        if not specAnOk:
            reason += "Spectrum analyzer not connected. "
        return DeviceInfo(
            name = "IF System",
            resource = "External switch and spectrum analyzer",
            connected = switchOk and specAnOk,
            reason = reason
        )

    @property
    def input_select(self) -> InputSelect:
        return self.externalSwitch.selected
    
    @input_select.setter
    def input_select(self, inputSelect: InputSelect):
        self.externalSwitch.selected = inputSelect
        
    def set_pol_sideband(self, pol: int = 0, sideband: int | str = 'USB') -> None:
        self.externalSwitch.select_pol_sideband(pol, sideband)

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
    def attenuation(self) -> float:
        return 0

    @attenuation.setter
    def attenuation(self, atten_dB: float):
        pass
   