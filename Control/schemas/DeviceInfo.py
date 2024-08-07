from pydantic import BaseModel
from typing import Optional

class DeviceInfo(BaseModel):
    '''
    Get the overall status and resource for a device
    '''
    name: str
    resource: str = "none"
    connected: bool = False
    reason: Optional[str] = None
