from DBBand6Cart.CartTests import CartTest
from Util.Singleton import Singleton
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

class MeasurementStatus(Singleton):
    def __init__(self):
        self.model = MeasurementStatusModel()

    def getCurrentValues(self):
        return self.model

    def setMeasuring(self, measuring: CartTest):
        self.model.cartTest = measuring
        self.model.timeStamp = datetime.now()
        if not measuring:
            self.model.complete = True

    def setChildKey(self, childKey: int):
        self.model.childKey = childKey
        self.model.timeStamp = datetime.now() 
        
    def getMeasuring(self):
        return self.model.cartTest

    def stopMeasuring(self):
        self.model.timeStamp = datetime.now()
        self.model.cartTest = None

    def isMeasuring(self):
        return self.model.cartTest is not None and not self.model.complete
    
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