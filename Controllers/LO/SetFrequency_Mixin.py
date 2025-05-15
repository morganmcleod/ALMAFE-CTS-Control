from AMB.LODevice import LODevice
from INSTR.SignalGenerator.Interface import SignalGenInterface
from Controllers.schemas.LO import LOSettings

class SetFrequency_Mixin():
    """ Shared implementation of set LO frequency is common to MTS1 and MTS2"""

    def __init__(self,
            loDevice: LODevice,
            refSynth: SignalGenInterface,
            coldMultiplier: int,
            warmMultiplier: int
    ):
        self.loDevice = loDevice
        self.refSynth = refSynth
        self.coldMultiplier = coldMultiplier
        self.warmMultiplier = warmMultiplier

    def setFrequency(self, 
            freqGHz: float,
            settings: LOSettings = None
        ) -> tuple[bool, str]:        
        if settings.setReference:
            sign = 1 if settings.lockSBSelect == LODevice.LOCK_BELOW_REF else -1            
            if not self.refSynth.setFrequency((freqGHz / self.coldMultiplier + (settings.floogOffset * sign)) / self.warmMultiplier):
                return False, "error setting synthesizer frequency"
            if not self.refSynth.setAmplitude(settings.refAmplitude):
                return False, "error setting synthesizer amplitude"
            if not self.refSynth.setRFOutput(True):
                return False, "error enabling synthesizer output"
        self.loDevice.selectLoopBW(settings.loopBWSelect)
        self.loDevice.selectLockSideband(settings.lockSBSelect)
        
        # not locking LO:
        if not settings.lockLO:
            wcaFreq, ytoFreq, ytoCourse = self.loDevice.setFrequency(freqGHz)
            if wcaFreq == 0:
                error = "frequency out of range"
            else:
                self.loDevice.setNullLoopIntegrator(True)
                return True, "tuned but not locked"
        
        # locking LO, loop increasing refAmplitude up to max:
        done = False
        error = False
        refAmplitude = settings.refAmplitude        
        while not done and not error:
            wcaFreq, ytoFreq, ytoCourse = self.loDevice.lockPLL(freqGHz)
            if wcaFreq == 0:
                # lock failed
                if settings.setReference and settings.refAmplitudeMax is not None and refAmplitude < settings.refAmplitudeMax:
                    # Increase reference amplitude if configured:
                    refAmplitude += 1
                    if not self.refSynth.setAmplitude(settings.refAmplitude):
                        error = "error setting synthesizer amplitude"
                else:
                    # set the zero integrator and warn:
                    wcaFreq, ytoFreq, ytoCourse = self.loDevice.setFrequency(freqGHz)
                    if wcaFreq == 0:
                        error = "frequency out of range"
                    else:
                        self.loDevice.setNullLoopIntegrator(True)
                        return True, "tuned but not locked"
            else:
                self.loDevice.clearUnlockDetect()
                done = True
        if error:
            return False, error
        else:
            return True, ""