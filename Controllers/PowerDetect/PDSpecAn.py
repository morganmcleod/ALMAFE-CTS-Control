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
        self._last_read = None
    
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
            deviceInfo = DeviceInfo.model_validate(self.spectrumAnalyzer.deviceInfo)
            deviceInfo.name = "Power detect"
            return deviceInfo
    
    @property
    def detect_mode(self) -> DetectMode:
        return DetectMode.SPEC_AN

    @property
    def units(self) -> Units:
        return Units.DBM

    def read(self, **kwargs) -> float | tuple[list[float], list[float]]:
        delay = kwargs.get('delay', None)
        if delay is None:
            sweepTime = self.spectrumAnalyzer.readSweepTime()
            delay = sweepTime * 2
        else:
            del kwargs['delay']
        self._last_read = self.spectrumAnalyzer.read(delay = delay, **kwargs)
        return self._last_read

    @property
    def last_read(self) -> float | tuple[list[float], list[float]]:
        return self._last_read

    def zero(self) -> None:
        pass