from .BaseMXA import BaseMXA
from .schemas import AveragingType, DetectorMode, InternalPreamp, TraceType, MarkerType, SpectrumAnalyzerSettings
import time

class SpectrumAnalyzer(BaseMXA):

    def __init__(self, resource="TCPIP0::10.1.1.10::inst0::INSTR", idQuery=True, reset=True) -> None:
        """Constructor

        :param str resource: VISA resource string, defaults to "GPIB0::13::INSTR"
        :param bool idQuery: If true, perform an ID query and check compatibility, defaults to True
        :param bool reset: If true, reset the instrument and set default configuration, defaults to True
        """
        super().__init__(resource, idQuery, reset)
        self.settings = SpectrumAnalyzerSettings()
        self.configFreqStartStop(4e9, 20e9)

    def configureAll(self, settings: SpectrumAnalyzerSettings):
        self.settings = settings
        self.configAcquisition(
            autoDetector = False,
            manualDetector = DetectorMode.AVERAGE,
            sweepPoints = settings.sweepPoints
        )
        self.configSweepCoupling(
            autoResolutionBW = settings.autoResolutionBW,
            resolutionBW = settings.resolutionBW,
            autoVideoBW = settings.autoVideoBW,
            videoBW = settings.videoBW,
            autoSweepTime = settings.autoSweepTime,
            sweepTime = settings.sweepTime
        )
        self.configTraceType(
            1, 
            TraceType.CLEAR_WRITE,
            enableUpdate = True,
            enableDisplay = True
        )
        self.configDetector(
            autoDetector = False,
            detector = DetectorMode.AVERAGE
        )
        self.configInternalPreamp(
            InternalPreamp.FULL_RANGE if settings.enableInternalPreamp else InternalPreamp.OFF
        )
        self.configLevel(
            autoAtten = False,
            manualAtten = settings.attenuation
        )
        self.configAveraging(
            count = settings.averagingCount if settings.enableAveraging else 1
        )

    def configNarrowBand(self, center: float, span: float) -> tuple[bool, str]:
        self.configMarkerType(1, MarkerType.OFF)
        self.configAcquisition(autoDetector = False, manualDetector = DetectorMode.NORMAL, sweepPoints = 1)
        self.configFreqCenterSpan(center * 1e9, span * 1e9)
        self.configMarkerType(1, MarkerType.NORMAL)
        code, msg = self.errorQuery()
        return code == 0, msg

    def measureNarrowBand(self) -> tuple[bool, str]:
        self.configTraceType(1, TraceType.AVERAGE)
        self.configAveraging(50, AveragingType.RMS)
        self.restartTrace()
        time.sleep(1)
        iter = 3
        done = False
        # retry a couple times if we get an unreasonable power level:
        while iter > 0 and not done:
            iter -= 1
            self.readMarker()
            if -100 < self.markerY < 20:
                done = True
        if iter == 0:
            return False, "SpectrumAnalyzer.measureNarrowBand: too many retries"
        else:
            return True, ""
        
    def endNarrowBand(self) -> tuple[bool, str]:
        self.configMarkerType(1, MarkerType.OFF)
        # self.configureAll(self.settings)

