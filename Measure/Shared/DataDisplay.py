from AMB.schemas.MixerTests import IVCurveResults, MagnetOptResults, DefluxResults
from Measure.MixerTests.ResultsQueue import ResultsQueue

class DataDisplay():

    def __init__(self) -> None:
        self.ivCurveQueue = ResultsQueue()
        self.magnetOptQueue = ResultsQueue()
        self.defluxQueue = ResultsQueue()
        self.ivCurveResults = IVCurveResults()
        self.magnetOptResults = MagnetOptResults()
        self.defluxResults = DefluxResults()        
        self.reset()

    def reset(self) -> None:
        self.warmIfData = None
        self.chopperPowerHistory = []
        self.specAnPowerHistory = None
        self.currentNoiseTemp = [None, None]
        self.yFactorHistory = []
        self.yFactorPowers = []
        self.timeSeriesList = []
        self.stabilityHistory = []
        self.biasOptResults = []
        self.ivCurveResults.reset()
        self.magnetOptResults.reset()
        self.defluxResults.reset()
