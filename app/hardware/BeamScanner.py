from CTSDevices.MotorControl.GalilDMCSocket import MotorController
from CTSDevices.MotorControl.MCSimulator import MCSimulator
from CTSDevices.PNA.schemas import MeasConfig, PowerConfig, MeasType, Format, SweepType, SweepGenType, TriggerSource
from CTSDevices.PNA.AgilentPNA import AgilentPNA
from CTSDevices.PNA.PNASimulator import PNASimulator
from Measure.BeamScanner.schemas import MeasurementSpec, ScanList, ScanListItem, SubScansOption
from Measure.BeamScanner.BeamScanner import BeamScanner
from hardware.ReferenceSources import loReference, rfReference
from hardware.FEMC import ccaDevice, loDevice, rfSrcDevice

motorController = MCSimulator()
motorController.setup()

pna = PNASimulator(resource="GPIB0::16::INSTR", idQuery=True, reset=True)
pna.setMeasConfig(MeasConfig())
pna.setPowerConfig(PowerConfig())

beamScanner = BeamScanner(motorController, pna, loReference, ccaDevice, loDevice, rfSrcDevice)

FOR_DEBUG_ONLY = True
if FOR_DEBUG_ONLY:
    beamScanner.rfReference = rfReference   # normally we don't use the RF reference synth.

beamScanner.measurementSpec = MeasurementSpec(
    resolution = 14,
    centerPowersInterval = 60
)

beamScanner.scanList = ScanList(
    items = [
        ScanListItem(RF = 211, LO=221, subScansOption = SubScansOption(copol0 = True, xpol0 = True, copol1 = True, xpol1=True, copol180=True)),
        ScanListItem(RF = 215, LO=225, subScansOption = SubScansOption(copol0 = True, xpol0 = True, copol1 = True, xpol1=True, copol180=True)),
        ScanListItem(RF = 219, LO=229, subScansOption = SubScansOption(copol0 = True, xpol0 = True, copol1 = True, xpol1=True, copol180=True)),
        ScanListItem(RF = 231, LO=241, subScansOption = SubScansOption(copol0 = True, xpol0 = True, copol1 = True, xpol1=True, copol180=True)),
        ScanListItem(RF = 235, LO=245, subScansOption = SubScansOption(copol0 = True, xpol0 = True, copol1 = True, xpol1=True, copol180=True)),
        ScanListItem(RF = 239, LO=249, subScansOption = SubScansOption(copol0 = True, xpol0 = True, copol1 = True, xpol1=True, copol180=True)),
        ScanListItem(RF = 243, LO=253, subScansOption = SubScansOption(copol0 = True, xpol0 = True, copol1 = True, xpol1=True, copol180=True)),
        ScanListItem(RF = 247, LO=257, subScansOption = SubScansOption(copol0 = True, xpol0 = True, copol1 = True, xpol1=True, copol180=True)),
        ScanListItem(RF = 262, LO=252, subScansOption = SubScansOption(copol0 = True, xpol0 = True, copol1 = True, xpol1=True, copol180=True)),
        ScanListItem(RF = 271, LO=261, subScansOption = SubScansOption(copol0 = True, xpol0 = True, copol1 = True, xpol1=True, copol180=True)),
        ScanListItem(RF = 275, LO=265, subScansOption = SubScansOption(copol0 = True, xpol0 = True, copol1 = True, xpol1=True, copol180=True))
    ]
)
beamScanner.scanList.updateIndex()
