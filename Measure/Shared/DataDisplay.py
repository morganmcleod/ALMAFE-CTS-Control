from AMB.schemas.MixerTests import IVCurveResults, MagnetOptResults, DefluxResults

class DataDisplay():

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.warmIfData = None
        self.chopperPowerHistory = []
        self.specAnPowerHistory = None
        self.currentNoiseTemp = [None, None]
        self.yFactorHistory = []
        self.stabilityHistory = []
        self.ivCurveResults = IVCurveResults()
        self.magnetOptResults = MagnetOptResults()
        self.defluxResults = DefluxResults()
