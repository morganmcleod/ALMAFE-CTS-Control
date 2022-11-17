import os
import sys
from os.path import dirname
import unittest

from CTSDevices.Tests.Unit.test_PowerMeter import test_PowerMeter

if __name__ == "__main__":
    try:
        unittest.main() # run all tests
    except SystemExit as e:
        pass # silence this exception
