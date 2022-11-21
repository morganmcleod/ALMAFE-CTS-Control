from pydantic import BaseModel
from CTSDevices.MotorControl.MCInterface import MotorStatus, MoveStatus, Position
from Procedures.BeamScanner.BeamScanner import ScanStatus, SubScansOption, ScanList, ScanListItem, MeasurementSpec

class ControllerQuery(BaseModel):
    """
    A low-level query to send to the beam scanner motor controller.    
    """
    request: str
    replySize: int
    def getText(self):
        return f"'{self.request}' with replySize {self.replySize}"
