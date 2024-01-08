import os
import sys
from os.path import dirname
import unittest
import logging

LOG_TO_FILE = True
LOG_FILE = 'CTSDevices_Unittest.log'

logger = logging.getLogger("ALMAFE-CTS-Control")
logger.setLevel(logging.DEBUG)
if LOG_TO_FILE:
    handler = logging.FileHandler(LOG_FILE)
else:
    handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(fmt = '%(asctime)s %(levelname)s:%(message)s'))
logger.addHandler(handler)

logger.info("-----------------------------------------------------------------")

from CTSDevices.Tests.Unit.test_KeysightE441X import test_PowerMeter
from CTSDevices.Tests.Unit.test_AgilentPNA import test_AgilentPNA
from CTSDevices.Tests.Unit.test_PNASimulator import test_PNASimulator
from CTSDevices.Tests.Unit.test_WarmIFPlate import test_WarmIFPlate
from CTSDevices.Tests.Unit.test_CartAssembly import test_CartAssembly
from CTSDevices.Tests.Unit.test_GalilDMCSocket import test_GalilDMCSocket
from CTSDevices.Tests.Unit.test_Lakeshore218 import test_Lakeshore218

if __name__ == "__main__":
    logger = logging.getLogger("ALMAFE-CTS-Control")
    logger.setLevel(logging.DEBUG)
    if LOG_TO_FILE:
        handler = logging.FileHandler(LOG_FILE)
    else:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt = '%(asctime)s %(levelname)s:%(message)s'))
    logger.addHandler(handler)
    try:
        unittest.main() # run all tests
    except SystemExit as e:
        pass # silence this exception
