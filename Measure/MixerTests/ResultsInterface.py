from abc import ABC, abstractmethod
from typing import Any
from .ResultsQueue import PointType

class ResultsInterface(ABC):
    @abstractmethod
    def put(self, 
            pol: int,
            sis: int,
            point: Any | list[Any],
            type: PointType = PointType.NORMAL
        ) -> None:
        pass