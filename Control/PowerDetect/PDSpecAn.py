import logging
from .Interface import PowerDetect_Interface, DetectMode
from INSTR.SpectrumAnalyzer.SpectrumAnalyzer import SpectrumAnalyzer, SpectrumAnalyzerSettings

class PDSpecAn(PowerDetect_Interface):

    def __init__(self, spectrumAnalyzer: SpectrumAnalyzer):
        self.spectrumAnalyzer = spectrumAnalyzer
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.reset()
    
    def reset(self):
        self.spectrumAnalyzer.reset()        
    
    def configure(self, **kwargs) -> None:
        config = kwargs.get('config', None)
        sweepPoints = kwargs.get('sweepPoints', None)
        startGHz = kwargs.get('startGHz', None)
        stopGHz = kwargs.get('stopGHz', None)

        if isinstance(config, SpectrumAnalyzerSettings):
            if sweepPoints:
                config.sweepPoints = sweepPoints
            self.spectrumAnalyzer.configureAll(config)

        if startGHz and stopGHz:
            success, msg = self.spectrumAnalyzer.configFreqStartStop(startGHz * 1e9, stopGHz * 1e9)
            if not success:
                self.logger.error(msg)

    @property
    def detect_mode(self) -> DetectMode:
        return DetectMode.SPEC_AN

    def read(self, **kwargs) -> float | tuple[list[float], list[float]]:
        averaging = kwargs.get('averaging', 1)
        delay = kwargs.get('delay', 1)
        if self.spectrumAnalyzer.narrowBand:
            success, msg = self.spectrumAnalyzer.measureNarrowBand(averaging, delay)
            if success:
                return self.spectrumAnalyzer.markerY
            self.logger.error(msg)
            return 0
        else:            
            success, msg = self.spectrumAnalyzer.configAveraging(averaging)
            if not success:
                self.logger.error(msg)
            success, msg = self.spectrumAnalyzer.readTrace()
            if success:
                return self.spectrumAnalyzer.traceX, self.spectrumAnalyzer.traceY
            self.logger.error(msg)
            return [], []

    def zero(self) -> None:
        pass