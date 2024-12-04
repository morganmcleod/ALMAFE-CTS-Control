import logging
from .Interface import PowerDetect_Interface, DeviceInfo, DetectMode, Units
from INSTR.SpectrumAnalyzer.SpectrumAnalyzer import SpectrumAnalyzer, SpectrumAnalyzerSettings
from DebugOptions import *

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
    def device_info(self) -> DeviceInfo:
        if SIMULATE:
            return DeviceInfo(
                name = 'Power detect',
                resource = 'simulated spectrum analyzer',
                connected = True
            )
        else:
            deviceInfo = DeviceInfo.parse_obj(self.spectrumAnalyzer.deviceInfo)
            deviceInfo.name = "Power detect"
            return deviceInfo
    
    @property
    def detect_mode(self) -> DetectMode:
        return DetectMode.SPEC_AN

    @property
    def units(self) -> Units:
        return Units.DBM

    def read(self, **kwargs) -> float | tuple[list[float], list[float]]:
        sweepTime = self.spectrumAnalyzer.readSweepTime()
        return self.spectrumAnalyzer.read(delay = sweepTime * 1.25, **kwargs)

    def zero(self) -> None:
        pass