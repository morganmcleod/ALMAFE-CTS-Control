from enum import Enum

class SelectSideband(Enum):
    USB = "USB"
    LSB = "LSB"
    BOTH = "BOTH"

    def testSB(self, sb: int | str):        
        if self == SelectSideband.BOTH:
            return True
        try:
            if self == SelectSideband.USB and (sb == 1 or sb.upper() == self.USB.value):
                return True
            if self == SelectSideband.LSB and (sb == 2 or sb.upper() == self.LSB.value):
                return True
        except:
            pass
        return False