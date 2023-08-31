from ..Common.RemoveDelims import removeDelims
import re
import pyvisa
import logging
import time

class TemperatureMonitor():
    DEFAULT_TIMEOUT = 10000

    def __init__(self, resource="GPIB0::12::INSTR", idQuery=True, reset=True):
        """Constructor

        :param str resource: VISA resource string, defaults to "GPIB0::12::INSTR"
        :param bool idQuery: If true, perform an ID query and check compatibility, defaults to True
        :param bool reset: If true, reset the instrument and set default configuration, defaults to True
        """
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        rm = pyvisa.ResourceManager()
        try:
            self.inst = rm.open_resource(resource)
            self.inst.timeout = self.DEFAULT_TIMEOUT
            ok = True
            if ok and idQuery:
                ok = self.idQuery()
            if ok and reset:
                ok = self.reset()
        except pyvisa.VisaIOError as err:
            self.logger.error(err)
            self.inst = None

    def __del__(self):
        """Destructor
        """
        if self.inst:
            self.inst.close()
            self.inst = None

    def idQuery(self):
        """Perform an ID query and check compatibility

        :return bool: True if the instrument is compatible with this class.
        """
        if not self.inst:
            return False

        mfr = None
        model = None
        response = self.inst.query("*IDN?")
        match = re.match(r"MODEL218", response, flags=re.IGNORECASE)
        if match:
            mfr = "Lakeshore"
            model = match.group()

        if mfr and model:
            self.logger.debug(mfr + " " + model)
            return True
        return False

    def reset(self):
        """Reset the instrument and set default configuration

        :return bool: True if instrument responed to Operation Complete query
        """
        if not self.inst:
            return False

        self.inst.write("*RST")
        time.sleep(0.25)
        self.inst.write("DFLT 99")
        return True

    def readSingle(self, input: int = 1):
        if not 1 <= input <= 8:
            return -1.0, 1
        temp = self.inst.querg(f"KRDG ? {input}\r\n")
        temp = float(removeDelims(temp))
        err = self.inst.query(f"RDGST? {input}\r\n")
        if err != 0:
            temp = -1
        return temp, err

    def readAll(self):
        temps = self.inst.query("KRDG ? 0\r\n")
        temps = removeDelims(temps)
        temps = [float(t) for t in temps]
        # check for range errors for each sensor:
        errors = []
        for i in range(8):
            err = self.inst.query(f"RDGST? {i + 1}\r\n")
            err = int(err.strip())
            if err != 0:
                temps[i] = -1
            errors.append(err)
        return temps, errors
