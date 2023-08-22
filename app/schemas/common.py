from pydantic import BaseModel
from typing import List, Any, Dict
from fastapi import Response
from fastapi.encoders import jsonable_encoder
import json

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

class SingleInt(BaseModel):
    '''
    For get/set a single float value.
    '''
    value: int
    def getText(self, units = None):
        return str(self.value) + (" " + units if units else "")