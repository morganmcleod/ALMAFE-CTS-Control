from .PNAInterface import *
from .BaseAgilentPNA import *
import time
from typing import Tuple
from statistics import mean
from math import log10, pi, sqrt, atan2
import logging

DEFAULT_CONFIG = MeasConfig(
    channel = 1,
    measType = MeasType.S21,
    format = Format.SDATA,
    sweepType = SweepType.CW_TIME,
    sweepGenType = SweepGenType.STEPPED,
    sweepPoints = 6000,
    triggerSource = TriggerSource.IMMEDIATE,
    bandWidthHz = 200,
    centerFreq_Hz = 10.180e9,
    spanFreq_Hz = 0,
    timeout_sec = 6.03,
    sweepTimeAuto = True,
    measName = "CH1_S21_CW"
)

FAST_CONFIG = MeasConfig(
    channel = 1,
    measType = MeasType.S21,
    format = Format.SDATA,
    sweepType = SweepType.CW_TIME,
    sweepGenType = SweepGenType.STEPPED,
    sweepPoints = 5,
    triggerSource = TriggerSource.MANUAL,
    bandWidthHz = 200,
    centerFreq_Hz = 10.180e9,
    spanFreq_Hz = 0,
    timeout_sec = 10,
    sweepTimeAuto = True,
    measName = "CH1_S21_CW"
)

DEFAULT_POWER_CONFIG = PowerConfig(
    channel = 1, 
    powerLevel_dBm = -10, 
    attenuation_dB = 0
)

class AgilentPNA(BaseAgilentPNA):

    def __init__(self, resource="GPIB0::16::INSTR", idQuery=True, reset=True):
        """Constructor

        :param str resource: VISA resource string, defaults to "GPIB0::13::INSTR"
        :param bool idQuery: If true, perform an ID query and check compatibility, defaults to True
        :param bool reset: If true, reset the instrument and set default configuration, defaults to True
        """
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.measConfig = None
        self.powerConfig = None
        super(AgilentPNA, self).__init__(resource, idQuery, reset)
    
    def reset(self) -> bool:
        """Reset instrument to defaults and set up measurment and power configuration
        :return bool: True if reset successful
        """
        super(AgilentPNA, self).reset()
        if self.measConfig:
            self.setMeasConfig(self.measConfig)
        if self.powerConfig:
            self.setPowerConfig(self.powerConfig)
        return True;

    def setMeasConfig(self, config:MeasConfig):
        """Set the measurement configuration for a channel
        :param MeasConfig config
        """
        self.measConfig = config
        # delete then re-create the measurement:
        measNames = self.listMeasurementParameters(config.channel)
        if measNames:
            self.configureMeasurementParameter(config.channel, Mode.DELETE, measName = measNames[0])
        self.configureMeasurementParameter(config.channel, Mode.CREATE, config.measType, config.measName)
        # display the trace:
        self.configureDisplayTrace(Mode.CREATE, measName = config.measName)
        # configure sweep generator, type, points
        self.configureSweep(config.channel,
                            config.sweepType,
                            config.sweepGenType,
                            config.timeout_sec,
                            config.sweepPoints,
                            config.sweepTimeAuto)
        # configure bandwidth, frequency, trigger
        self.configureBandwidth(config.channel, config.bandWidthHz)
        self.configureFreqCenterSpan(config.channel, config.centerFreq_Hz, config.spanFreq_Hz)
        # 0.5ms delay on triggering so multiple points aren't measured from one trigger pulse:
        self.setTriggerSweepSignal(config.triggerSource, 
                                   TriggerScope.CURRENT_CHANNEL if config.triggerSource == TriggerSource.EXTERNAL else TriggerScope.ALL_CHANNELS,
                                   TriggerLevel.HIGH,
                                   0.0005)
        self.configureTriggerChannel(config.channel, triggerPoint = True, mode = TriggerMode.CONTINUOUS)
        # Use BNC1 for external trigger:
        self.inst.write(":CONT:SIGN BNC1,TILHIGH;")
        time.sleep(1)

    def setPowerConfig(self, config:PowerConfig):
        """Set the output power and attenuation configuration for a channel
        :param PowerConfig config
        """
        self.powerConfig = config
        self.configurePowerAttenuation(config.channel, config.attenuation_dB)
        self.configurePowerLevel(config.channel, config.powerLevel_dBm)
        self.configurePowerState(True)

    def getTrace(self, *args, **kwargs) -> Tuple[List[float], List[float]]:
        """Get trace data as a list of float
        :return Tuple[List[float], List[float]]
        """
        if self.measConfig.triggerSource == TriggerSource.MANUAL:
            for _ in range(self.measConfig.sweepPoints):
                self.generateTriggerSignal(self.measConfig.channel, True)
                time.sleep(0.1)
        
        sweepComplete = False
        startTime = time.time()
        elapsed = 0
        while not sweepComplete and elapsed < self.measConfig.timeout_sec:
            sweepComplete = self.checkSweepComplete(waitForComplete = False)
            elapsed = time.time() - startTime
        
        if sweepComplete:
            data = self.readData(self.measConfig.channel, self.measConfig.format, self.measConfig.sweepPoints, self.measConfig.measName)
            if data:
                real_a = data[::2]
                imag_a = data[1::2]
                # not taking sqrt because the value we want is power, not voltage:
                amp = [10 * log10(real ** 2 + imag ** 2) for real, imag in zip(real_a, imag_a)]
                phase = [atan2(imag, real) * 180 / pi for real, imag in zip(real_a, imag_a)]
                return amp, phase
            else:
                self.logger.error("getTrace no data")
        else:
            self.logger.error("getTrace timeout")
        return None, None
            
    def getAmpPhase(self) -> Tuple[float]:
        """Get instantaneous amplitude and phase
        :return (amplitude_dB, phase_deg)
        """
        if self.measConfig.triggerSource == TriggerSource.MANUAL:
            for _ in range(self.measConfig.sweepPoints):
                self.generateTriggerSignal(self.measConfig.channel, True)
                time.sleep(0.1)
        if self.checkSweepComplete(waitForComplete = True):
            trace = self.readData(self.measConfig.channel, self.measConfig.format, self.measConfig.sweepPoints, self.measConfig.measName)
            # Real and imaginary values are interleaved in the trace data
            # Average these then convert to phase & amplitude
            real = mean(trace[::2])
            imag = mean(trace[1::2])
            # not taking sqrt because the value we want is power, not voltage:
            amp = 10 * log10(real ** 2 + imag ** 2)
            phase = atan2(imag, real) * 180 / pi
            return (amp, phase)
        else:
            self.logger.error(f"getAmpPhase error: checkSweepComplete returned False")
            return (None, None)

    def workaroundPhaseLockLost(self):
        """The E8362B in CTS2 reports PHASE LOCK LOST if the frequency range extends above ~13 GHz
        This workaround is to clear that error state.  It is harmless to run on other units.
        """
        self.configureFreqCenterSpan(
            channel = 1,
            centerFreq_Hz = 6e9,
            spanFreq_Hz = 12e9
        )
        code, msg = self.errorQuery()
        while code:
            code, msg = self.pna.errorQuery()
