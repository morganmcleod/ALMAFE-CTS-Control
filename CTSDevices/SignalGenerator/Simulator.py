
class SignalGenSimulator():

    def __init__(self, reset=True):
        """Constructor
        """
        if reset:
            self.reset()


    def idQuery(self, doPrint = False):
        """Perform an ID query and check compatibility

        :return bool: True if the instrument is compatible with this class.
        """
        return True

    def reset(self):
        self.frequency = 20E9
        self.amplitude = -20
        self.enabled = False
        return True

    def errorQuery(self):
        """Send an error query and return the results

        :return (int, str): Error code and string
        """
        return (0, "No error")

    def isConnected(self) -> bool:
        return True
    
    def setAmplitude(self, amp_dB:float) -> bool:
        self.amplitude = amp_dB
        return True

    def setFrequency(self, freq_GHz:float) -> bool:
        self.frequency = freq_GHz
        return True
        
    def setRFOutput(self, enable:bool) -> bool:
        self.enabled = enable
        return True
        
    def getAmplitude(self) -> float:
        return self.amplitude

    def getFrequency(self) -> float:
        return self.frequency

    def getRFOutput(self) -> bool:
        return self.enabled
