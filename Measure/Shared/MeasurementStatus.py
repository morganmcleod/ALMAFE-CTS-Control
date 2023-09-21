from DBBand6Cart.CartTests import CartTest
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MeasurementStatus(BaseModel):
    cartTest: Optional[CartTest] = None
    childKey: int = 0
    timeStamp: Optional[datetime] = None
    stepComplete: bool = False
    allComplete: bool = False
    message: str = None
    error: bool = False

    def setMeasuring(self, measuring: CartTest):
        self.cartTest = measuring
        self.timeStamp = datetime.now()
        if not measuring:
            self.stepComplete = self.allComplete = True

    def setChildKey(self, childKey: int):
        self.childKey = childKey
        self.timeStamp = datetime.now() 
        
    def getMeasuring(self):
        return self.cartTest

    def stopMeasuring(self):
        self.timeStamp = datetime.now()
        self.cartTest = None

    def isMeasuring(self):
        return self.cartTest is not None and not self.allComplete
    
    def setStatusMessage(self, msg):
        self.timeStamp = datetime.now()
        self.message = msg

    def getStatusMessage(self):
        return self.message

    def setComplete(self, step = None, all = None):
        self.timeStamp = datetime.now()
        if step is not None:
            self.stepComplete = step
        if all is not None:
            self.allComplete = all

    def setError(self, error: bool):
        self.timeStamp = datetime.now()
        self.error = error

