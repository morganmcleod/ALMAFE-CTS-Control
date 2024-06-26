import unittest
import configparser
from AMB.AMBConnectionDLL import AMBConnectionDLL
from AMB.LODevice import LODevice
from AMB.CCADevice import CCADevice
from DBBand6Cart.CartConfigs import CartConfigs
from DBBand6Cart.schemas.CartConfig import CartKeys
from DBBand6Cart.schemas.MixerParam import MixerParam
from DBBand6Cart.schemas.PreampParam import PreampParam
from DBBand6Cart.MixerParams import MixerParams
from DBBand6Cart.PreampParams import PreampParams

from FEMC.CartAssembly import CartAssembly

CARTRIDGE_BAND = 6
YTO_LOW = 12.22
YTO_HIGH = 14.77
CARTRIDGE_CONFIG = 433

class test_CartAssembly(unittest.TestCase):

    def setUp(self) -> None:
        config = configparser.ConfigParser()
        config.read('FrontEndAMBDLL.ini')
        dllName = config['load']['dll']
        self.conn = AMBConnectionDLL(channel = 0, dllName = dllName)
        self.ccaDevice = CCADevice(self.conn, nodeAddr = 0x13, band = CARTRIDGE_BAND)
        self.ccaDevice.setFeMode(self.ccaDevice.MODE_TROUBLESHOOTING)
        self.ccaDevice.setBandPower(CARTRIDGE_BAND, True)
        self.ccaDevice.setSIS(0, 1, 0, 0)
        self.ccaDevice.setSIS(0, 2, 0, 0)
        self.ccaDevice.setSIS(1, 1, 0, 0)
        self.ccaDevice.setSIS(2, 2, 0, 0)
        self.ccaDevice.setLNAEnable(False)

        self.loDevice = LODevice(self.conn, nodeAddr = 0x13, band = CARTRIDGE_BAND)
        self.loDevice.setBandPower(CARTRIDGE_BAND, True)
        self.loDevice.setYTOLimits(YTO_LOW, YTO_HIGH)

        self.cartAssembly = CartAssembly(self.ccaDevice, self.loDevice)
        return super().setUp()

    def tearDown(self) -> None:
        self.ccaDevice.setBandPower(CARTRIDGE_BAND, False)
        self.ccaDevice.shutdown()
        self.loDevice.shutdown()
        self.conn.shutdown()
        return super().tearDown()

    def test_setConfig(self) -> None:
        self.cartAssembly.setConfig(CARTRIDGE_CONFIG)
        self.assertIsInstance(self.cartAssembly.keysPol0, CartKeys)
        self.assertIsInstance(self.cartAssembly.keysPol1, CartKeys)
        self.assertIsInstance(self.cartAssembly.mixerParams01, list)
        self.assertIsInstance(self.cartAssembly.mixerParams02, list)
        self.assertIsInstance(self.cartAssembly.mixerParams11, list)
        self.assertIsInstance(self.cartAssembly.mixerParams12, list)
        self.assertIsInstance(self.cartAssembly.mixerParams01[0], MixerParam)
        self.assertIsInstance(self.cartAssembly.mixerParams02[0], MixerParam)
        self.assertIsInstance(self.cartAssembly.mixerParams11[0], MixerParam)
        self.assertIsInstance(self.cartAssembly.mixerParams12[0], MixerParam)
        self.assertIsInstance(self.cartAssembly.preampParams01, list)
        self.assertIsInstance(self.cartAssembly.preampParams02, list)
        self.assertIsInstance(self.cartAssembly.preampParams11, list)
        self.assertIsInstance(self.cartAssembly.preampParams12, list)
        self.assertIsInstance(self.cartAssembly.preampParams01[0], PreampParam)
        self.assertIsInstance(self.cartAssembly.preampParams02[0], PreampParam)
        self.assertIsInstance(self.cartAssembly.preampParams11[0], PreampParam)
        self.assertIsInstance(self.cartAssembly.preampParams12[0], PreampParam)
        self.assertTrue(self.cartAssembly.configId == CARTRIDGE_CONFIG)
        self.assertIsNone(self.cartAssembly.mixerParam01)
        self.assertIsNone(self.cartAssembly.mixerParam02)
        self.assertIsNone(self.cartAssembly.mixerParam11)
        self.assertIsNone(self.cartAssembly.mixerParam12)

    def test_setRecevierBias(self) -> None:
        self.cartAssembly.setConfig(CARTRIDGE_CONFIG)
        self.cartAssembly.setRecevierBias(221)
        self.assertIsInstance(self.cartAssembly.mixerParam01, MixerParam)
        self.assertIsInstance(self.cartAssembly.mixerParam02, MixerParam)
        self.assertIsInstance(self.cartAssembly.mixerParam11, MixerParam)
        self.assertIsInstance(self.cartAssembly.mixerParam12, MixerParam)
        sis = self.cartAssembly.ccaDevice.getSIS(0, 1, 10)
        self.assertAlmostEqual(sis['Vj'], self.cartAssembly.mixerParam01.VJ, delta = 0.1)
        sis = self.cartAssembly.ccaDevice.getSIS(0, 2, 10)
        self.assertAlmostEqual(sis['Vj'], self.cartAssembly.mixerParam02.VJ, delta = 0.1)
        sis = self.cartAssembly.ccaDevice.getSIS(1, 1, 10)
        self.assertAlmostEqual(sis['Vj'], self.cartAssembly.mixerParam11.VJ, delta = 0.1)
        sis = self.cartAssembly.ccaDevice.getSIS(1, 2, 10)
        self.assertAlmostEqual(sis['Vj'], self.cartAssembly.mixerParam12.VJ, delta = 0.1)

    def test_setAutoLOPower(self) -> None:
        self.cartAssembly.setConfig(CARTRIDGE_CONFIG)
        self.cartAssembly.loDevice.lockPLL(221)
        self.cartAssembly.setRecevierBias(221)
        self.cartAssembly.setAutoLOPower()
    
    def test_getSISCurrentTargets(self) -> None:
        self.cartAssembly.setConfig(CARTRIDGE_CONFIG)
        self.cartAssembly.setRecevierBias(221)
        targets = self.cartAssembly.getSISCurrentTargets()
        print(targets)

