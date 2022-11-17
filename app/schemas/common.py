from pydantic import BaseModel

class SingleBool(BaseModel):
    '''
    For get/set a single bool value.
    '''
    value: bool
    def getText(self):
        return "true" if self.value else "false"
    
class SingleFloat(BaseModel):
    '''
    For get/set a single float value.
    '''
    value: float
    def getText(self, units = None):
        return str(self.value) + (" " + units if units else "")