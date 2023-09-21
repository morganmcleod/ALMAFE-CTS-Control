import logging

class TemperatureMonitorSimulator():

    SIM_DATA = [3.5, 3.9, 4.1, 15, 110, 273, 274, 275]
    SIM_ERRS = [0, 0, 0, 0, 0, 0, 0, 0]

    def __init__(self):
        self.logger = logging.getLogger("ALMAFE-CTS-Control")

    def idQuery(self):
        self.logger.debug("TemperatureMonitorSimulator")

    def readSingle(self, input: int):
        if not 1 <= input <= 8:
            return -1.0, 1 
        return self.SIM_DATA[input - 1], self.SIM_ERRS[input - 1]

    def readAll(self):
        return self.SIM_DATA, self.SIM_ERRS