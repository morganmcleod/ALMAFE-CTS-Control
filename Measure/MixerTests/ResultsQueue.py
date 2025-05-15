import queue
from enum import Enum
from typing import Any
from pydantic import BaseModel

class PointType(Enum):
    START = 0       # send as or before first point of each curve
    NORMAL = 1      # all normal points
    GAP = 2         # send when there is a discontinuous gap in the trace
    END = 3         # send after each curve
    ALL_DONE = 9    # send after all curves are done

class Item(BaseModel):
    pol: int
    sis: int
    points: list[Any]
    type: PointType = PointType.NORMAL

class ResultsQueue():
    def __init__(self, queue2 = None):
        self.queue = queue.SimpleQueue()
        self.queue2 = queue2
    
    def put(self, 
            pol: int,
            sis: int,
            points: Any | list[Any],
            type: PointType = PointType.NORMAL
        ) -> None:
        if not isinstance(points, list):
            points = [points]
        self.queue.put(Item(
            pol = pol,
            sis = sis,
            points = points,
            type = type
        ))
        if self.queue2 is not None:
            self.queue2.put(pol, sis, points, type)

    def get_nowait(self):
        return self.queue.get_nowait()
