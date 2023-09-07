from pydantic import BaseModel

class MotorStatus(BaseModel):
    xPower: bool = False
    yPower: bool = False
    polPower: bool = False
    xMotion: bool = False
    yMotion: bool = False
    polMotion: bool = False
    polTorque: float = 0

    def powerFail(self) -> bool:
        return not (self.xPower and self.yPower and self.polPower)

    def inMotion(self) -> bool:
        return self.xMotion or self.yMotion or self.polMotion  

    def getText(self) -> str:
        return f"powerFail={self.powerFail()} inMotion={self.inMotion()} polTorque={self.polTorque}"

class MoveStatus(BaseModel):
    success: bool = False
    powerFail: bool = False
    timedOut: bool = False
    stopSignal: bool = False

    def isError(self) -> bool:
        return self.powerFail or self.timedOut

    def shouldStop(self) -> bool:
        return self.success or self.stopSignal or self.isError()

    def getText(self) -> str:
        return f"success={self.success}, powerFail={self.powerFail}, timedOut={self.timedOut}, stopSignal={self.stopSignal}"


class Position(BaseModel):
    x: float = 0
    y: float = 0
    pol: float = 0

    def __eq__(self, other) -> bool:
        if not other:
            return False
        return self.x == other.x and \
            self.y == other.y and \
            abs(self.pol - other.pol) < 0.2

    def calcMove(self, dest):
        return Position(x = self.x - dest.x,
                        y = self.y - dest.y,
                        pol = self.pol - dest.pol)

    def getText(self) -> str:
        return f"({self.x}, {self.y}, {self.pol})"
    
class ControllerQuery(BaseModel):
    """
    A low-level query to send to the beam scanner motor controller.    
    """
    request: str
    replySize: int
    def getText(self):
        return f"'{self.request}' with replySize {self.replySize}"