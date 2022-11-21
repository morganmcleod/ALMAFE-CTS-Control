from CTSDevices.MotorControl.GalilDMCSocket import MotorController
from CTSDevices.MotorControl.MCSimulator import MCSimulator
from Procedures.BeamScanner.BeamScanner import BeamScanner, MeasurementSpec, ScanList, ScanListItem

motorController = MCSimulator()
motorController.setup()
beamScanner = BeamScanner(motorController)

beamScanner.measurementSpec = MeasurementSpec(
    resolution = 14,
    centerPowersInterval = 60
)

beamScanner.scanList = ScanList(
    items = [
        ScanListItem(RF = 211, LO=221),
        ScanListItem(RF = 215, LO=225),
        ScanListItem(RF = 219, LO=229),
        ScanListItem(RF = 231, LO=241),
        ScanListItem(RF = 235, LO=245),
        ScanListItem(RF = 239, LO=249),
        ScanListItem(RF = 243, LO=253),
        ScanListItem(RF = 247, LO=257),
        ScanListItem(RF = 262, LO=252),
        ScanListItem(RF = 271, LO=261),
        ScanListItem(RF = 275, LO=265)
    ]
)
beamScanner.scanList.updateIndex()
