import os
import sys
from os.path import dirname
import unittest

# from CTSDevices.Tests.Unit.test_KeysightE441X import test_PowerMeter
# from CTSDevices.Tests.Unit.test_AgilentPNA import test_AgilentPNA
# from CTSDevices.Tests.Unit.test_PNASimulator import test_PNASimulator
from CTSDevices.Tests.Unit.test_IFProcessor import test_IFProcessor

if __name__ == "__main__":
    try:
        unittest.main() # run all tests
    except SystemExit as e:
        pass # silence this exception
