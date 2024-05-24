from CTSDevices.Common.RemoveDelims import removeDelims
from CTSDevices.Common.VisaInstrument import VisaInstrument
import re
import logging
import time
from threading import Lock

class TemperatureMonitor():
    DEFAULT_TIMEOUT = 10000

    def __init__(self, resource="GPIB0::12::INSTR", idQuery=True, reset=True):
        """Constructor

        :param str resource: VISA resource string, defaults to "GPIB0::12::INSTR"
        :param bool idQuery: If true, perform an ID query and check compatibility, defaults to True
        :param bool reset: If true, reset the instrument and set default configuration, defaults to True
        """
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.lock = Lock()        
        self.inst = VisaInstrument(resource, timeout = self.DEFAULT_TIMEOUT, read_termination = '\n', write_termination = '\n')
        ok = self.isConnected()
        if ok and idQuery:
            ok = self.idQuery()
        if ok and reset:
            ok = self.reset()

    def __del__(self):
        """Destructor
        """
        if self.inst:
            self.inst.close()
            self.inst = None

    def isConnected(self) -> bool:
        if not self.inst.connected:
            return False
        try:
            result = self.inst.query("QESR?\r")
            result = removeDelims(result)
            return len(result) > 0
        except:
            return False

    def idQuery(self):
        """Perform an ID query and check compatibility

        :return bool: True if the instrument is compatible with this class.
        """
        if not self.inst:
            return False

        mfr = None
        model = None
        with self.lock:
            response = self.inst.query("*IDN?\r")
        match = re.search(r"MODEL218", response, flags=re.IGNORECASE)
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
        return True

    def readSingle(self, input: int):
        if not 1 <= input <= 8:
            return -1.0, 1
        with self.lock:
            temp = self.inst.query(f"KRDG? {input}\r")
        time.sleep(0.25)
        with self.lock:
            err = self.inst.query(f"RDGST? {input}\r")
        try:
            temp = float(removeDelims(temp)[0])
        except:
            temp = -1.0
        try:
            err = int(removeDelims(err)[0])
        except:
            err = 0
        if err != 0:
            temp = -1
        return temp, err

    def readAll(self):
        with self.lock:
            temps = self.inst.query("KRDG?\r")
        time.sleep(0.25)
        with self.lock:
            errors = self.inst.query("RDGST?\r")
        try:
            temps = removeDelims(temps)            
            temps = [float(temps[i]) for i in range(8)]
        except:
            return [-1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0], [1, 1, 1, 1, 1, 1, 1, 1]
        try:
            errors = removeDelims(errors)
            errors = [int(errors[i]) for i in range(8)]
        except:
            errors = [0, 0, 0, 0, 0, 0, 0, 0]
        for i in range(len(errors)):
            if errors[i] != 0:
                temps[i] = -1.0
        return temps, errors
