from enum import Enum

class SelectPolarization(Enum):
    POL0 = "POL0"
    POL1 = "POL1"
    BOTH = "BOTH"

    def testPol(self, pol: int):        
        if self == SelectPolarization.BOTH:
            return True
        if self == SelectPolarization.POL0 and pol == 0:
            return True
        if self == SelectPolarization.POL1 and pol == 1:
            return True
        return False