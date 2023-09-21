from pydantic import BaseModel
from typing import List

DESCRIPTIONS = [
    '4K stage',
    '4K (LS332)',
    '15K stage',
    '110K stage',
    'RF source',
    'RF receiver',
    'Ambient',
    'LN2 overflow'
]

class Temperatures(BaseModel):
    temps: List[float] = [-1, -1, -1, -1, -1, -1, -1, -1]
    errors: List[int] = [1, 1, 1, 1, 1, 1, 1, 1]
    descriptions: List[str] = DESCRIPTIONS
