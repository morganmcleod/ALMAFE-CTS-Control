from .BaseE441X import BaseE441X, Channel, Trigger, Unit
from pydantic import BaseModel
from time import time
from enum import Enum
from statistics import mean, stdev
from math import sqrt

class StdErrConfig(BaseModel):
    minS: int = 1       # minimum num samples
    maxS: int = 100     # maximum num samples
    stdErr: float = 1   # target standard error
    timeout: int = 0    # seconds

    class UseCase(Enum):
        MIN_SAMPLES = 1      # minS samples, ignore stdErr and timeout
        MAX_SAMPLES = 2      # minS to maxS samples, stop if stdErr achieved
        MIN_TO_TIMEOUT = 3   # at least minS samples, stop at timeout
        MOVING_WINDOW = 4    # at least maxS samples, maxS moving window, stop if stdErr achieved or timeout
        TIMEOUT = 5          # sample for timeout seconds

    def getUseCase(self):
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
    success: bool = False
    N: int = 0
    mean: float = 0
    stdErr: float = 0
    CI95U: float = 0
    CI95L: float = 0
    time: float = 0  # seconds

class PowerMeter(BaseE441X):

    def __init__(self, resource="GPIB0::13::INSTR", idQuery=True, reset=True):
        super(PowerMeter, self).__init__(resource, idQuery, reset)
        self.settings = {Channel.A : {}, Channel.B: {}}
        self.setDefaults()
        
    def setDefaults(self):
        self.setUnits(Unit.DBM)
        self.setFastMode(False)
        self.disableAveraging()

    def setUnits(self, units: Unit, channel = None):
        if not channel or channel == Channel.A:
            self.inst.write(f"UNIT1:POW {units.value}")
            self.settings[Channel.A]['units'] = units
        if (not channel or channel == Channel.B) and self.twoChannel:
            self.inst.write(f"UNIT2:POW {units.value}")
            self.settings[Channel.B]['units'] = units

    def setFastMode(self, fastMode, channel = None):
        s = 'SPE 200' if fastMode else 'SPE 40'
        if not channel or channel == Channel.A:
            self.inst.write(f"SENS1:{s}")
            self.configureTrigger(Trigger.IMMEDIATE, Channel.A)
            self.initiateContinuous(True, Channel.A)
            self.settings[Channel.A]['fastMode'] = fastMode
        if (not channel or channel == Channel.B) and self.twoChannel:
            self.inst.write(f"SENS2:{s}")
            self.configureTrigger(Trigger.IMMEDIATE, Channel.B)
            self.initiateContinuous(True, Channel.B)
            self.settings[Channel.B]['fastMode'] = fastMode
    
    def disableAveraging(self, channel = None):
        # set the display to show both channels, if applicable
        # turn off averaging and set the CW frequency to 6 GHz
        if not channel or channel == Channel.A:
            self.configureMeasurement(Channel.A, units = self.settings[Channel.A].get('units', Unit.DBM))
            self.inst.write("SENS1:AVER:STAT 0")
            self.inst.write("SENS1:FREQ:CW 6E9")
            self.initiateContinuous(True, Channel.A)
        if (not channel or channel == Channel.B) and self.twoChannel:
            self.configureMeasurement(Channel.B, units = self.settings[Channel.B].get('units', Unit.DBM))
            self.inst.write("SENS2:AVER:STAT 0")
            self.inst.write("SENS2:FREQ:CW 6E9")
            self.initiateContinuous(True, Channel.B)

    def autoRead(self, channel = Channel.A):
        if channel == Channel.B and not self.twoChannel:
            return False
        wasFast = self.settings[channel].get('fastMode', False)
        if wasFast:
            self.setFastMode(False, channel)
        self.timeout = 60000
        self.configureTrigger(Trigger.IMMEDIATE, channel)
        self.configureMeasurement(channel, units = self.settings[channel].get('units', Unit.DBM))
        value = self.readMeasurement(channel)
        self.timeout = self.DEFAULT_TIMEOUT
        self.disableAveraging()
        if wasFast:
            self.setFastMode(True, channel)
        return value
        
    def averagingRead(self, config: StdErrConfig, channel = Channel.A):
        if channel == Channel.B and not self.twoChannel:
            return False
        useCase = config.getUseCase()
        done = False
        success = False
        S = []
        N = 0
        start = time()
        while not done:
            S.append(self.readSingle(channel))
            N += 1
            if useCase == StdErrConfig.UseCase.MIN_SAMPLES:
                if N >= config.minS:
                    done = True
                    success = True
            
            elif useCase == StdErrConfig.UseCase.MAX_SAMPLES:
                if N >= config.minS:
                    if N > 1 and stdev(S) / sqrt(N) <= config.stdErr:
                        done = True
                        success = True
                    elif N >= config.maxS:
                        done = True
                        success = False
            
            elif useCase == StdErrConfig.UseCase.MIN_TO_TIMEOUT:
                if N >= config.minS and time() - start >= config.timeout:
                    done = True
                    success = stdev(S) / sqrt(N) <= config.stdErr
            
            elif useCase == StdErrConfig.UseCase.MOVING_WINDOW:
                if N >= config.maxS:
                    if stdev(S[:config.maxS]) / sqrt(config.maxS) <= config.stdErr:
                        done = True
                        success = True
                    elif time() - start >= config.timeout:
                        done = True
                        success = False

            elif useCase == StdErrConfig.UseCase.TIMEOUT:
                if time() - start >= config.timeout:
                    done = True
                    success = True

        if useCase == StdErrConfig.UseCase.MOVING_WINDOW and N >= config.maxS:
            stdErr = stdev(S[:config.maxS]) / sqrt(config.maxS)
        elif N > 1:
            stdErr = stdev(S) / sqrt(N)
        else:
            stdErr = 0

        A = mean(S) if N else 0
        return StdErrResult(
            success = success,
            N = N,
            mean = A,
            stdErr = stdErr,
            CI95U = A + 1.96 * stdErr,
            CI95L = A - 1.96 * stdErr,
            time = time() - start
        )
        




                








        






