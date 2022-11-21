'''
Data models and interface for three-axis motor controller
'''
from abc import ABC, abstractmethod
from pydantic import BaseModel, List
from typing import Tuple
from enum import Enum

class MeasType(Enum):
    S11 = "S11"
    S12 = "S12"
    S21 = "S21"
    S22 = "S22"
    A = "A"
    B = "B"
    R1 = "R1"
    R2 = "R2"
    AB = "AB"
    BA = "BA"

class Format(Enum):
    FDATA = 0   # formatted trace data from measResult location
    SDATA = 1   # corrected complex trace data from rawMeas location
    FMEM = 2    # formatted memory data from memResult location
    SMEM = 3    # corrected complex data from rawMemory location
    SDIV = 4    # complex data from Normalization Divisor location

class SweepType(Enum):
    LIN_FREQ = 0
    LOG_FREQ = 1
    POWER_SWEEP = 2
    CW_TIME = 3
    SEGMENT_SWEEP = 4

class SweepGenType(Enum):
    ANALOG = 0  # The sweep is controlled by an internally generated sweep ramp. 
                # The phase lock loop maintains the proper association with the measurement. 
                # This mode is faster than STEPPED. Sweep time can be set in this mode.

    STEPPED = 1 # The analyzer phase locks the source and receiver at each frequency point
                # before making a measurement. This mode is more accurate than ANALOG.
                # Dwell time can be set in this mode.

class TriggerSource(Enum):
    IMMEDIATE = 0   # Internal source sends continuous trigger signals
    EXTERNAL = 1    # External (rear panel) source 
    MANUAL = 2      # Sends one trigger signal when manually triggered from the front panel
                    # or software trigger is sent.


class MeasConfig(BaseModel):
    channel: int = 1         # in 1..32
    measType: MeasType = MeasType.S21
    format: Format = Format.SDATA
    sweepType: SweepType = SweepType.CW_TIME
    sweepGenType: SweepGenType = SweepGenType.STEPPED
    sweepPoints: int = 20    # in 2..16001
    triggerSource: TriggerSource = TriggerSource.MANUAL
    bandWidthHz: int = 700   # in 1..250000.  Not all values are supported.
                             # Analyzer will round up to the next valid setting.
    centerFreq_Hz: int = 6e9 # Valid range is instrument-dependent
    spanFreq_Hz: int = 1e9   # Valid range is instrument-dependent.  Typical is 10e6..20e9
    timeout_sec: float = 10  # Sets selected channel sweep time value, if sweepGenType is ANALOG,
                             # or sets the selected channel dwell time value, if sweepGenType is STEPPED. 
                             # Note: Only set if "Sweep Time Auto" is "Off".

class PowerConfig(BaseModel):
    channel: int = 1                # in 1..32
    powerLevel_dBm: float = -10.0   # Channel output power in -90..+20
    attenuation_dB: float = 0.0     # Channel attenuation in 0..70
                                    # Note: Step is 10 dB. If a number other than these is entered, 
                                    # the analyzer will select the next lower valid value. For example, 
                                    # if 19.9 is entered, the analyzer will switch in 10 dB attenuation.

class PNAInterface(ABC):

    @abstractmethod
    def idQuery(self) -> bool:
        """Perform an ID query and check compatibility
        :return bool: True if the instrument is compatible with this class.
        """
        pass

    @abstractmethod
    def reset(self) -> bool:
        """Reset instrument to defaults
        :return bool: True if reset successful
        """
        pass

    @abstractmethod
    def setMeasConfig(self, config: MeasConfig):
        """Set the measurement configuration for a channel
        :param MeasConfig config
        """
        pass

    @abstractmethod
    def setPowerConfig(self, config: PowerConfig):
        """Set the output power and attenuation configuration for a channel
        :param PowerConfig config
        """
        pass

    @abstractmethod
    def getTrace(self) -> List[float]:
        """Get trace data as a list of float
        :return List[float]
        """
        pass

    
    @abstractmethod
    def getAmpPhase(self) -> Tuple[List[float], List[float]]:
        """Get trace data as parallel lists of amplitude dB, phase deg
        :return Tuple[List[float], List[float]]
        """
        pass
