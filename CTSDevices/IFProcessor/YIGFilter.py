from .HP3488a import *

class YIGFilter():
    """The YIG filter in the IF processor"""
    
    MAX_TUNING_MHZ = 12400      # upper limit in MHz
    STEP_RESOLUTION = 2.7839    # resolution in MHz/step
    LATCH_BIT = 4096            # latch the new tuning

    def __init__(self, resource="GPIB0::13::INSTR", idQuery=True, reset=True):
        """Constructor

        :param str resource: VISA resource string, defaults to "GPIB0::13::INSTR"
        :param bool idQuery: If true, perform an ID query and check compatibility, defaults to True
        :param bool reset: If true, reset the instrument and set default configuration, defaults to True
        """
        self.switchController = SwitchController(resource)
        self.switchController.writeConfig = SwitchConfig(
            taskType = TaskType.DIGITAL,
            slot = 3,
            port = DigitalPort.WORD_16BIT,
            method = DigitalMethod.ASCII
            dataStream = 3
        )
        self.freqGhz = 0

    def setFrequency(self, freqGHz: float) -> None:
        if freqGHz < 0:
            freqGHz = 0
        elif freqGHz > (self.MAX_TUNING_MHZ / 1000):
            freqGHz = (self.MAX_TUNING_MHZ / 1000)
        self.freqGhz = freqGHz

        tuningWord = int((self.MAX_TUNING_MHZ - (1000 * freqGHz)) / self.STEP_RESOLUTION)

        data = [tuningWord, tuningWord + self.LATCH_BIT, tuningWord]
        self.switchController.digitalWrite(data)

    def getFrequency(self) -> float:
        return self.freqGhz        

