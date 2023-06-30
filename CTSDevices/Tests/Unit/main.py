import os
import sys
from os.path import dirname
import unittest

from .test_KeysightE441X import test_PowerMeter
from .test_AgilentPNA import test_AgilentPNA
from .test_PNASimulator import test_PNASimulator
from .test_IFProcessor import test_IFProcessor

if __name__ == "__main__":
    try:
        unittest.main() # run all tests
    except SystemExit as e:
        pass # silence this exception
