from pydantic import BaseModel
from enum import Enum

class StdErrConfig(BaseModel):
    """Configuration inputs for PowerMeter.averagingRead()

    minS: minimum number of samples to read.  If 0 then read until timeout (TIMEOUT mode)
    maxS: maximum/window size samples.  If 0 then read until timeout (TIMEOUT or MIN_TO_TIMEOUT mode)
    stdErr: target standard error of samples to achieve.  If 0 then read until timeout or just read min samples (TIMEOUT or MIN_SAMPLES mode)
    timeout: seconds.  If 0 then read either min or max samples (MIN_SAMPLES or MAX_SAMPLES mode)
    """
    minS: int = 1
    maxS: int = 100
    stdErr: float = 1
    timeout: int = 0

    class UseCase(Enum):
        """Use cases supported by PowerMeter.averagingRead():
        MIN_SAMPLES:  read min samples, ignore stdErr and timeout
        MAX_SAMPLES:  read min samples, continue up to max samples, stop if stdErr target achieved
        MIN_TO_TIMEOUT:  read min samples, continue until timeout, stop if stdErr target achieved
        MOVING_WINDOW:  read at least max samples, continue with max size moving window, stop if timeout or stdErr target achieved
        TIMEOUT:  read for timeout seconds
        """
        MIN_SAMPLES = 1
        MAX_SAMPLES = 2
        MIN_TO_TIMEOUT = 3
        MOVING_WINDOW = 4
        TIMEOUT = 5 

    def getUseCase(self):
        """Determine the UseCase based on the provided values

        :return UseCase
        """
        if self.stdErr == 0 and self.minS == 0 and self.maxS == 0:
            return self.UseCase.TIMEOUT
        elif self.stdErr == 0 and self.timeout == 0:
            return self.UseCase.MIN_SAMPLES
        elif self.timeout == 0:
            return self.UseCase.MAX_SAMPLES
        elif self.maxS == 0:
            return self.UseCase.MIN_TO_TIMEOUT
        else:
            return self.UseCase.MOVING_WINDOW

class StdErrResult(BaseModel):
    """Result type returned by PowerMeter.averagingRead()

    success: True if the target standard error was achieved for the use cases which support it.  Otherwise True if measurement completed. 
    N: Number of samples taken.  May be larger than maxS in MOVING_WINDOW mode.
    mean: of the samples or window
    stdErr: of the samples or window
    CI95U: 95% upper confidence interval of the mean
    CI95L: 95% lower confidence interval of the mean
    useCase: which StdErrConfig UseCase was selected
    time: seconds of total time taken while sampling
    """
    success: bool = False
    N: int = 0
    mean: float = 0
    stdErr: float = 0
    CI95U: float = 0
    CI95L: float = 0
    useCase: StdErrConfig.UseCase = StdErrConfig.UseCase.TIMEOUT
    time: float = 0
    
class Channel(Enum):
    A = 1
    B = 2

class Unit(Enum):
    DBM = "DBM"
    W = "W"

class Trigger(Enum):
    IMMEDIATE = "IMM"
    BUS = "BUS"
    HOLD = "HOLD"
    EXTERNAL = "EXT"
    INTERNAL_A = "INT1"
    INTERNAL_B = "INT2"
