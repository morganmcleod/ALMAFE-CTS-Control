from pydantic import BaseModel
from typing import List

class CryostatTemperatures(BaseModel):
    temps: List[float] = [-1, -1, -1, -1, -1, -1, -1, -1]
    errors: List[int] = [1, 1, 1, 1, 1, 1, 1, 1]
