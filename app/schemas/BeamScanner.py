from pydantic import BaseModel
from abc import ABC, abstractmethod
from CTSDevices.MotorControl.schemas import MotorStatus, MoveStatus, Position
from Measure.BeamScanner.schemas import ScanStatus, SubScansOption, ScanList, ScanListItem, MeasurementSpec
from CTSDevices.PNA.schemas import MeasConfig, PowerConfig

class ControllerQuery(BaseModel):
    """
    A low-level query to send to the beam scanner motor controller.    
    """
    request: str
    replySize: int
    def getText(self):
        return f"'{self.request}' with replySize {self.replySize}"
