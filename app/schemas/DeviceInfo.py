from pydantic import BaseModel

class DeviceInfo(BaseModel):
    '''
    For get/set a single bool value.
    '''
    name: str
    resource_name: str = "none"
    is_connected: bool = False
