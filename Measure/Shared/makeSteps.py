from typing import List, Optional
from DebugOptions import *

def makeSteps(start: float, stop: float, step: float, extras: Optional[List[float]] = None, round_decimals: int = 6):
    if stop <= start or step <= 0:
        steps = [round(start, round_decimals)]
    else:
        steps = [round(start + i * step, round_decimals) for i in range(int((stop - start) / step + 1))]
    if extras:
        steps += [round(x, round_decimals) for x in extras]
    return steps
