class WarmIFPlate():
    def __init__(self, attenuator, inputSwitch, noiseSource, outputSwitch, yigFilter):
        self.attenuator = attenuator
        self.inputSwitch = inputSwitch
        self.noiseSource = noiseSource
        self.outputSwitch = outputSwitch
        self.yigFilter = yigFilter

    def isConnected(self) -> bool:
        return self.attenuator.isConnected() and \
            self.inputSwitch.isConnected() and \
            self.noiseSource.isConnected() and \
            self.outputSwitch.isConnected() and \
            self.yigFilter.isConnected()
