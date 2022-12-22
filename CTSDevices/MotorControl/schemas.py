from pydantic import BaseModel

class MotorStatus(BaseModel):
    xPower: bool
    yPower: bool
    polPower: bool
    xMotion: bool
    yMotion: bool
    polMotion: bool

    def powerFail(self) -> bool:
        return not (self.xPower and self.yPower and self.polPower)

    def inMotion(self) -> bool:
        return self.xMotion or self.yMotion or self.polMotion  

    def getText(self) -> str:
        return f"powerFail={self.powerFail()} inMotion={self.inMotion()}"

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
            abs(self.pol - other.pol) < 0.1

    def calcMove(self, dest):
        return Position(x = self.x - dest.x,
                        y = self.y - dest.y,
                        pol = self.pol - dest.pol)

    def getText(self) -> str:
        return f"({self.x}, {self.y}, {self.pol})"