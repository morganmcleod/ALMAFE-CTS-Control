from pydantic import BaseModel

class ReferenceSourceStatus(BaseModel):
    '''
    LO/RF reference source status
    '''
    freqGHz: float
    ampDBm: float
    enable: bool
    def getText(self):
        return f"{self.freqGHz} GHz @ {self.ampDBm} dBm, {'enabled' if self.enable else 'disabled'}"
