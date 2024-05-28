import logging
from .schemas import *
import numpy as np

class SpectrumAnalyzerSimulator():
    """Base class for Agilent/Keysight MXA spectrum analyzers
    Provides common functionality available from all models.
    """

    def __init__(self,  idQuery=True, reset=True) -> None:
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.mfr = None
        self.model = None
        ok = self.isConnected()
        if ok and idQuery:
            ok = self.idQuery()
        if ok and reset:
            ok = self.reset()

    def isConnected(self) -> bool:
        return True
        
    def idQuery(self):
        """Perform an ID query and check compatibility

        :return bool: True if the instrument is compatible with this class.
        """
        self.mfr = "NRAO"
        self.model = "SpectrumAnalyzerSimulator"
        return True

    def reset(self):
        """Reset the instrument and set default configuration

        :return bool: True if instrument responed to Operation Complete query
        """
        self.traceX = []
        self.traceY = []
        self.internalPreamp = InternalPreamp.OFF
        self.averagingCount = 1
        self.averagingType = AveragingType.AUTO
        self.freqStart = 0 
        self.freqStop = 26e9
        self.freqCenter = 13e9
        self.freqSpan = 26e9
        self.refLevel = 0
        self.refLevelOffset = 0
        self.units = LevelUnits.DBM
        self.autoAtten = True
        self.manualAtten = 10
        self.continuous = True
        self.autoDetector = True
        self.manualDetector = DetectorMode.NORMAL
        self.acqTraceNum = 1
        self.logVertical = True
        self.scalePerDiv = 10
        self.sweepPoints = 1001
        self.autoResolutionBW = True
        self.resolutionBW = 3e6
        self.autoVideoBW = True
        self.videoBW = 3e6
        self.autoSweepTime = True
        self.sweepTime = 0.0663
        self.autoVBWRBWRatio = True
        self.VBWRBWRatio = 1
        self.typeTraceNum = 1
        self.traceType = TraceType.CLEAR_WRITE
        self.enableUpdate = False
        self.enableDisplay = False
        self.autoDetector: bool = True
        self.detector: DetectorMode = DetectorMode.AVERAGE
        self.autoRefChannel: bool = True
        self.refChannel: DetectorMode = DetectorMode.AVERAGE
        self.markerNum = 1
        self.markerType = MarkerType.NORMAL
        self.markerReadout = MarkerReadout.AUTO
        self.refMarkerNum = 12
        self.autoGateTime = True
        self.gateTime = 0.1
        self.enableFreqCounter = False
        self.smoothTraceNum = 1
        self.smoothNumPoints = 1
        return True
        
    def errorQuery(self) -> tuple[int, str]:
        """Send an error query and return the results

        :return (int, str): Error code and string
        """
        return 0, ""

    def configInternalPreamp(self, setting: InternalPreamp) -> tuple[bool, str]:
        self.internalPreamp = setting
        return True, f"SASim: Set internal preamp to {setting.value}"

    def configAveraging(self, 
            count: int = 100,
            type: AveragingType = AveragingType.AUTO) -> tuple[bool, str]:
        self.averagingCount = count
        self.averagingType = type
        return True, f"SASim: Set averagimg preamp to {count}, type {type.value}"

    def configFreqStartStop(self, startHz: float, stopHz: float) -> tuple[bool, str]:
        self.freqStart = startHz
        self.freqStop = stopHz
        return True, f"SASim: Set frequency start:{startHz}, stop:{stopHz}"
    
    def configFreqCenterSpan(self, centerHz: float, spanHz: float) -> tuple[bool, str]:
        self.freqCenter = centerHz
        self.freqSpan = spanHz
        return True, f"SASim: Set frequency center:{centerHz}, span:{spanHz}"
    
    def configLevel(self, 
            refLevel: float = 0, 
            refLevelOffset: float = 0, 
            units: LevelUnits = LevelUnits.DBM,
            autoAtten: bool = True,
            manualAtten: float = 10) -> tuple[bool, str]:
        self.refLevel = refLevel
        self.refLevelOffset = refLevelOffset
        self.units = units
        self.autoAtten = autoAtten
        self.manualAtten = manualAtten
        atten = "atten:auto" if autoAtten else f"atten:{manualAtten}"
        return True, f"SASim: refLevel:{refLevel}, offset:{refLevelOffset}, units:{units.value}, atten:{atten}"
    
    def configAcquisition(self,
            continuous: bool = True,
            autoDetector: bool = True,
            manualDetector: DetectorMode = DetectorMode.NORMAL,
            traceNum: int = 1,
            logVertical: bool = True,        
            scalePerDiv: float = 10,
            sweepPoints: int = 1001) -> tuple[bool, str]:
        self.continuous = continuous
        self.autoDetector = autoDetector
        self.manualDetector = manualDetector
        self.acqTraceNum = traceNum
        self.logVertical = logVertical
        self.scalePerDiv = scalePerDiv
        self.sweepPoints = sweepPoints
        det = "det:auto" if autoDetector else f"det:{manualDetector.value}"
        return True, f"SASim: acquire continuous:{continuous}, {det}, trace:{traceNum}, logVertical:{logVertical}, perDiv:{scalePerDiv}, points:{sweepPoints}"

    def configSweepCoupling(self,
            autoResolutionBW: bool = True,
            resolutionBW: float = 3e6,
            autoVideoBW: bool = True,
            videoBW: float = 3e6,
            autoSweepTime: bool = True,
            sweepTime: float = 0.0663,
            autoVBWRBWRatio: bool = True,
            VBWRBWRatio: float = 1) -> tuple[bool, str]:
        
        self.autoResolutionBW = autoResolutionBW
        self.resolutionBW = resolutionBW
        self.autoVideoBW = autoVideoBW
        self.videoBW = videoBW
        self.autoSweepTime = autoSweepTime
        self.sweepTime = sweepTime
        self.autoVBWRBWRatio = autoVBWRBWRatio
        self.VBWRBWRatio = VBWRBWRatio
        resBW = "res.BW:auto" if autoResolutionBW else f"res.BW:{resolutionBW}"
        vidBW = "vid.BW:auto" if autoVideoBW else f"vid.BW:{videoBW}"
        swTime = "sweep time:auto" if autoSweepTime else f"sweep time:{sweepTime}"
        ratio = "VBW/RBW ratio:auto" if autoVBWRBWRatio else f"VBW/RBW ratio:{VBWRBWRatio}"
        return True, f"SASim: {resBW}, {vidBW}, {swTime}, {ratio}"

    def configTraceType(self,
            traceNum: int = 1,
            type: TraceType = TraceType.CLEAR_WRITE,
            enableUpdate: bool = False,
            enableDisplay: bool = False) -> tuple[bool, str]:
        self.typeTraceNum = traceNum
        self.traceType = type
        self.enableUpdate = enableUpdate
        self.enableDisplay = enableDisplay
        return True, f"SASim: trace:{traceNum}, type:{type.value}, update:{enableUpdate}, display:{enableDisplay}"

    def configDetector(self,
            autoDetector: bool = True,
            detector: DetectorMode = DetectorMode.AVERAGE,
            autoRefChannel: bool = True,
            refChannel: DetectorMode = DetectorMode.AVERAGE) -> tuple[bool, str]:
        self.autoDetector = autoDetector
        self.detector = detector
        self.autoRefChannel = autoRefChannel
        self.refChannel = refChannel
        det = "detector:auto" if autoDetector else f"detector:{detector}"
        ref = "ref.channel:auto" if autoRefChannel else f"ref.channel:{refChannel}"
        return True, f"SASim: {det}, {ref}"

    def configMarkerType(self,
            markerNum: int = 1,
            type: MarkerType = MarkerType.NORMAL,
            readout: MarkerReadout = MarkerReadout.AUTO,
            refMarkerNum: int = 12,
            autoGateTime: bool = True,
            gateTime: float = 0.1,
            enableFreqCounter: bool = False) -> tuple[bool, str]:
        self.markerNum = markerNum
        self.markerType = type
        self.markerReadout = readout
        self.refMarkerNum = refMarkerNum
        self.autoGateTime = autoGateTime
        self.gateTime = gateTime
        self.enableFreqCounter = enableFreqCounter
        gate = "gate time:auto" if autoGateTime else f"gate time:{gateTime}"
        return True, f"SASim: marker:{markerNum}, type:{type.value}, readout:{readout.value}, ref:{refMarkerNum}, {gate}, freqCount:{enableFreqCounter}"
            
    def configSmoothing(self, traceNum:int = 1, numPoints: int = 1) -> tuple[bool, str]:
        self.smoothTraceNum = traceNum
        self.smoothNumPoints = numPoints
        return True, f"SASim: smoothing trace:{traceNum}, points:{numPoints}"

    def readTrace(self, traceNum:int = 1, timeout: int = 30) -> tuple[bool, str]:
        self.traceX = np.linspace(self.freqStart, self.freqStop, self.sweepPoints).tolist()
        self.traceY = np.random.normal(-32, 1, self.sweepPoints).tolist()
        return True, ""