class IFProcessor():
    def __init__(self, attenuator, inputSwitch, noiseSource, outputSwitch, yigFilter):
        self.attenuator = attenuator
        self.inputSwitch = inputSwitch
        self.noiseSource = noiseSource
        self.outputSwitch = outputSwitch
        self.yigFilter = yigFilter
