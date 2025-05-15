import hardware.BeamScanner
import hardware.ReferenceSources
import hardware.FEMC
import hardware.IFSystem
import app_Common.measProcedure.MeasurementStatus
from Measure.BeamScanner.schemas import ScanList, ScanListItem, SubScansOption
from Measure.BeamScanner.BeamScanner import BeamScanner
from DebugOptions import *
import copy

beamScanner = BeamScanner(
    motorController = hardware.BeamScanner.motorController, 
    pna = hardware.BeamScanner.pna, 
    loReference = hardware.ReferenceSources.loReference, 
    cartAssembly = hardware.FEMC.cartAssembly, 
    rfSrcDevice = hardware.FEMC.rfSrcDevice, 
    ifSystem = hardware.IFSystem.ifSystem,
    measurementStatus = app_Common.measProcedure.MeasurementStatus.measurementStatus()
)

if TESTING:
    defaultScanList = ScanList(
        items = [
            ScanListItem(RF = 231, LO=241, subScansOption = SubScansOption(copol0 = True, xpol0 = True, copol1 = True, xpol1 = True, copol180 = True))
        ]
    )
else:
    defaultScanList = ScanList(
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

beamScanner.scanList = copy.copy(defaultScanList)
beamScanner.scanList.updateIndex()
