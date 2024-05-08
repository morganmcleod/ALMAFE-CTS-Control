from CTSDevices.Common.RemoveDelims import removeDelims
from .schemas import Channel, Trigger, Unit, StdErrConfig, StdErrResult
from .BaseE441X import BaseE441X
from time import time
from statistics import mean, stdev
from math import sqrt

class PowerMeter(BaseE441X):
    """CTS/FETMS Power meter class which adds capaibilties to the base class.
    """

    def __init__(self, resource="GPIB0::13::INSTR", idQuery=True, reset=True):
        """Constructor

        :param str resource: VISA resource string, defaults to "GPIB0::13::INSTR"
        :param bool idQuery: If true, perform an ID query and check compatibility, defaults to True
        :param bool reset: If true, reset the instrument and set default configuration, defaults to True
        """
        super().__init__(resource, idQuery, reset)
        self.settings = {Channel.A : {}, Channel.B: {}}
        self.setDefaults()
        
    def setDefaults(self):
        """Set instrument defaults so that the front panel shows live readings

        :return bool: True if instrument responed to Operation Complete query
        """
        ok = self.setUnits(Unit.DBM)
        if ok:
            ok = self.setFastMode(False)
        if ok:
            ok = self.disableAveraging()
        return ok

    def setTimeout(self, timeoutMs: int = None):
        """Set the VISA timeout

        :param int timeoutMs: milliseconds
        """
        self.inst.timeout = timeoutMs if timeoutMs else self.DEFAULT_TIMEOUT

    def setUnits(self, units: Unit, channel = None):
        """Set power meter units

        :param Unit units: DBM or W
        :param Channel channel: which channel to configure, defaults to None which configures both channels if supported
        :return bool: True if instrument responed to Operation Complete query
        """
        if not channel or channel == Channel.A:
            self.inst.write(f"UNIT1:POW {units.value};")
            self.settings[Channel.A]['units'] = units
        if (not channel or channel == Channel.B) and self.twoChannel:
            self.inst.write(f"UNIT2:POW {units.value};")
            self.settings[Channel.B]['units'] = units
        opc = removeDelims(self.inst.query("*OPC?"))
        return opc and opc[0]

    def setFastMode(self, fastMode:bool, channel = None):
        """Set/clear 200 readings/second fast mode

        :param fastMode: set fast mode if true
        :param Channel channel: which channel to configure, defaults to None which configures both channels if supported
        :return bool: True if instrument responed to Operation Complete query
        """
        s = 'SPE 200' if fastMode else 'SPE 40'
        if not channel or channel == Channel.A:
            self.inst.write(f"SENS1:{s};")
            self.configureTrigger(Trigger.IMMEDIATE, Channel.A)
            self.initContinuous(True, Channel.A)
            self.settings[Channel.A]['fastMode'] = fastMode
        if (not channel or channel == Channel.B) and self.twoChannel:
            self.inst.write(f"SENS2:{s};")
            self.configureTrigger(Trigger.IMMEDIATE, Channel.B)
            self.initContinuous(True, Channel.B)
            self.settings[Channel.B]['fastMode'] = fastMode
        opc = removeDelims(self.inst.query("*OPC?"))
        return opc and opc[0]
    
    def disableAveraging(self, channel = None):
        """Set the display to show both channels, if applicable, turns off averaging and sets the CW frequency to 6 GHz

        :param Channel channel: which channel to configure, defaults to None which configures both channels if supported
        :return bool: True if instrument responed to Operation Complete query
        """
        if not channel or channel == Channel.A:
            self.configMeasurement(Channel.A, units = self.settings[Channel.A].get('units', Unit.DBM))
            self.inst.write("SENS1:AVER:STAT 0;")
            self.inst.write("SENS1:FREQ:CW 6E9;")
            self.initContinuous(True, Channel.A)
        if (not channel or channel == Channel.B) and self.twoChannel:
            self.configMeasurement(Channel.B, units = self.settings[Channel.B].get('units', Unit.DBM))
            self.inst.write("SENS2:AVER:STAT 0;")
            self.inst.write("SENS2:FREQ:CW 6E9;")
            self.initContinuous(True, Channel.B)
        opc = removeDelims(self.inst.query("*OPC?"))
        return opc and opc[0]

    def autoRead(self, channel = Channel.A):
        """Perform an auto-read which takes as long as needed to get (typically) three digits of resolution
        
        :param Channel channel: which channel to read, defaults to Channel.A
        :return float: power level
        """
        if channel == Channel.B and not self.twoChannel:
            return False
        wasFast = self.settings[channel].get('fastMode', False)
        if wasFast:
            self.setFastMode(False, channel)
        # self.setTimeout(60000)
        self.configureTrigger(Trigger.IMMEDIATE, channel)
        self.configMeasurement(channel, units = self.settings[channel].get('units', Unit.DBM))
        self.initImmediate(channel)
        value = self.read(channel)
        self.setTimeout()
        self.disableAveraging()
        if wasFast:
            self.setFastMode(True, channel)
        return value
        
    def averagingRead(self, config: StdErrConfig, channel = Channel.A):
        """Read multiple samples and average, as configured by StdErrConfig

        :param config: StdErrConfig to set up the measurement requirements.  See StdErrConfig for details.
        :param Channel channel: which channel to read, defaults to Channel.A
        :return StdErrResult: see StdErrResult for details.
        """
        if channel == Channel.B and not self.twoChannel:
            return False
        useCase = config.getUseCase()
        done = False
        success = False
        S = []
        N = 0
        start = time()
        while not done:
            S.append(self.read(channel))
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
            useCase = useCase,
            time = time() - start
        )
