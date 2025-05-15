from enum import Enum

class SelectSIS(Enum):
    BOTH = -1
    SIS1 = 1
    SIS2 = 2

    def testSis(self, sis: int):        
        if self == SelectSIS.BOTH:
            return True
        if self == SelectSIS.SIS1 and sis == 1:
            return True
        if self == SelectSIS.SIS2 and sis == 2:
            return True
        return False
