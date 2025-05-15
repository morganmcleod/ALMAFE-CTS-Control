from DBBand6Cart.CartTests import CartTest
from DBBand6Cart.MixerTests import MixerTest
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MeasurementStatusModel(BaseModel):
    testRecord: Optional[CartTest|MixerTest] = None
    childKey: int = 0
    timeStamp: Optional[datetime] = None
    complete: bool = True
    message: str = None
    error: bool = False
    stopNow: bool = False

class MeasurementStatus():
    def __init__(self):
        self.model = MeasurementStatusModel()

    def getCurrentValues(self):
        return self.model

    def setMeasuring(self, measuring: CartTest | MixerTest | None):
        self.model.timeStamp = datetime.now()
        self.model.testRecord = measuring
        self.model.stopNow = False        
        self.model.error = False            
        if measuring is None:
            self.model.complete = True

    def setChildKey(self, childKey: int):
        self.model.timeStamp = datetime.now() 
        self.model.childKey = childKey
        
    def getMeasuring(self):
        return self.model.testRecord

    def stopMeasuring(self):
        self.model.timeStamp = datetime.now()
        self.model.testRecord = None
        self.model.stopNow = True

    def isMeasuring(self):
        return self.model.testRecord is not None and not self.model.complete
    
    def stopNow(self):
        return self.model.stopNow

    def setStatusMessage(self, msg: str, error: bool = False):
        self.model.timeStamp = datetime.now()
        self.model.message = msg
        self.model.error = error

    def getStatusMessage(self):
        return self.model.message

    def setComplete(self, complete: bool):
        self.model.timeStamp = datetime.now()
        if complete is not None:
            self.model.complete = complete

    def setError(self, msg: str):
        self.model.timeStamp = datetime.now()
        self.model.error = True
        self.model.complete = True
        self.model.testRecord = None
        self.model.message = msg