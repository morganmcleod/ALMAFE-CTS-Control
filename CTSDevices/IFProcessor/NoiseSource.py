from CTSDevices.TestEquipment.AgilentE363xA import PowerSupply

class NoiseSource():
    """Noise diode implemented in terms of a Agilent E363xA power supply"""
    def __init__(self, resource="GPIB0::5::INSTR"):
        self.powerSupply = PowerSupply(resource)
        self.reset()

    def reset(self) -> None:
        self.powerSupply.setOutputEnable(False)
        self.powerSupply.setCurrentLimit(0.04)
        self.powerSupply.setVoltage(28)

    def setEnable(self, enable: bool = False) -> None:
        self.powerSupply.setOutputEnable(enable)

