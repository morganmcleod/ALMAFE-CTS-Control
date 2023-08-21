from DBBand6Cart.CartTests import CartTest

class Measuring():
    def __init__(self):
        self.cartTest = None

    def setMeasuring(self, measuring: CartTest):
        self.cartTest = measuring

    def getMeasuring(self):
        return self.cartTest

    def stopMeasuring(self):
        self.cartTest = None


measuring = Measuring()
