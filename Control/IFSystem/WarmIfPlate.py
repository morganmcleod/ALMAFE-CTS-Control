from .Interface import IFSystem_Interface, OutputSelect
from INSTR.WarmIFPlate import WarmIFPlate
from INSTR.InputSwitch.Interface import InputSelect
from INSTR.WarmIFPlate.OutputSwitch import OutputSelect as WIFOutputSelect, LoadSelect, PadSelect

class IFSystem(IFSystem_Interface):

    def __init__(self, warmIFPlate: WarmIFPlate):
        self.warmIFPlate = warmIFPlate
        self.reset()

    def reset(self) -> None:
        self.warmIFPlate.outputSwitch.setValue(OutputSelect.POWER_METER, LoadSelect.THROUGH, PadSelect.PAD_OUT)
        self.warmIFPlate.inputSwitch.selected = InputSelect.POL0_USB
        self.warmIFPlate.yigFilter.setFrequency(0.0)
        self.warmIFPlate.attenuator.setValue(20.0)
        self.outputSelect = OutputSelect.NONE

    @property
    def input_select(self) -> InputSelect:
        return self.warmIFPlate.inputSwitch.selected
    
    @input_select.setter
    def input_select(self, inputSelect: InputSelect):
        self.warmIFPlate.inputSwitch.selected = inputSelect
        
    def set_pol_sideband(self, pol: int = 0, sideband: int | str = 'USB') -> None:
        self.warmIFPlate.set_pol_sideband(pol, sideband)

    @property
    def output_select(self) -> OutputSelect:
        return self.outputSelect
    
    @output_select.setter
    def output_select(self, outputSelect: OutputSelect):
        if outputSelect == OutputSelect.POWER_DETECT:
            self.warmIFPlate.outputSwitch.setValue(WIFOutputSelect.POWER_METER, LoadSelect.THROUGH, PadSelect.PAD_OUT)
        elif outputSelect == OutputSelect.PNA_INTERFACE:
            self.warmIFPlate.outputSwitch.setValue(OutputSelect.SQUARE_LAW, LoadSelect.THROUGH, PadSelect.PAD_OUT)
        elif outputSelect == OutputSelect.LOAD:
            self.warmIFPlate.outputSwitch.setValue(WIFOutputSelect.POWER_METER, LoadSelect.LOAD, PadSelect.PAD_OUT)
    
    @property
    def frequency(self) -> float:
        return self.warmIFPlate.yigFilter.getFrequency
    
    @frequency.setter
    def frequency(self, freq_GHz: float):
        self.warmIFPlate.yigFilter.setFrequency(freq_GHz)

    @property
    def attenuation(self) -> float:
        return self.warmIFPlate.attenuator.getValue()

    @attenuation.setter
    def attenuation(self, atten_dB: float):
        self.warmIFPlate.attenuator.setValue(atten_dB)
