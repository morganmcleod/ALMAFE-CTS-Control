from pydantic import BaseModel

class SingleBool(BaseModel):
    '''
    For setting a single bool value in a PUT or POST operation.
    '''
    enable: bool
    def getText(self):
        return "enabled" if self.enable else "disabled"
    
class SingleFloat(BaseModel):
    '''
    For setting or reading single float value in a PUT or POST operation.
    '''
    value: float
    def getText(self, units = None):
        return str(self.value) + (" " + units if units else "")