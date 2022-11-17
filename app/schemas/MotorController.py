from pydantic import BaseModel

from CTSDevices.MotorControl.GalilDMCSocket import GPosition, GMotorStatus

class Position(GPosition):
    pol: float = 0

