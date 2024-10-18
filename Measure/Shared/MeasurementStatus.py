from DBBand6Cart.CartTests import CartTest
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MeasurementStatusModel(BaseModel):
    cartTest: Optional[CartTest] = None
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

    def setMeasuring(self, measuring: CartTest | None):
        self.model.timeStamp = datetime.now()
        self.model.cartTest = measuring
        self.model.stopNow = False
        if measuring is None:
            self.model.complete = True

    def setChildKey(self, childKey: int):
        self.model.timeStamp = datetime.now() 
        self.model.childKey = childKey
        
    def getMeasuring(self):
        return self.model.cartTest

    def stopMeasuring(self):
        self.model.timeStamp = datetime.now()
        self.model.cartTest = None
        self.model.stopNow = True

    def isMeasuring(self):
        return self.model.cartTest is not None and not self.model.complete
    
    def stopNow(self):
        return self.model.stopNow

    def setStatusMessage(self, msg):
        self.model.timeStamp = datetime.now()
        self.model.message = msg

    def getStatusMessage(self):
        return self.model.message

    def setComplete(self, complete = None):
        self.model.timeStamp = datetime.now()
        if complete is not None:
            self.model.complete = complete

    def setError(self, error: bool):
        self.model.timeStamp = datetime.now()
        self.model.error = error