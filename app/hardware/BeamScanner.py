from CTSDevices.MotorControl.GalilDMCSocket import MotorController
from CTSDevices.MotorControl.MCSimulator import MCSimulator
from CTSDevices.PNA.schemas import MeasConfig, PowerConfig, MeasType, Format, SweepType, SweepGenType, TriggerSource
from CTSDevices.PNA.AgilentPNA import AgilentPNA
from CTSDevices.PNA.PNASimulator import PNASimulator
from Measure.BeamScanner.schemas import MeasurementSpec, ScanList, ScanListItem, SubScansOption
from Measure.BeamScanner.BeamScanner import BeamScanner

motorController = MCSimulator()
motorController.setup()

pna = PNASimulator(resource="GPIB0::16::INSTR", idQuery=True, reset=True)
pna.setMeasConfig(MeasConfig())
pna.setPowerConfig(PowerConfig())

beamScanner = BeamScanner(motorController, pna)

beamScanner.measurementSpec = MeasurementSpec(
    resolution = 14,
    centerPowersInterval = 60
)

beamScanner.scanList = ScanList(
    items = [
        ScanListItem(RF = 211, LO=221, subScansOption = SubScansOption(copol0 = True, xpol0 = True, copol1 = False, xpol1=False, copol180=False))
        # ScanListItem(RF = 215, LO=225),
        # ScanListItem(RF = 219, LO=229),
        # ScanListItem(RF = 231, LO=241),
        # ScanListItem(RF = 235, LO=245),
        # ScanListItem(RF = 239, LO=249),
        # ScanListItem(RF = 243, LO=253),
        # ScanListItem(RF = 247, LO=257),
        # ScanListItem(RF = 262, LO=252),
        # ScanListItem(RF = 271, LO=261),
        # ScanListItem(RF = 275, LO=265)
    ]
)
beamScanner.scanList.updateIndex()
