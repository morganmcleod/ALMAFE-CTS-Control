
class DataDisplay():

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.warmIfData = None
        self.chopperPowerHistory = []
        self.specAnPowerHistory = None
        self.currentNoiseTemp = [None, None]
        self.yFactorHistory = []


