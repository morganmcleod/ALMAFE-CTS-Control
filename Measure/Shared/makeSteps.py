from CTSDevices.WarmIFPlate.InputSwitch import InputSelect
from typing import List, Optional, Tuple, Union
from DebugOptions import *

def makeSteps(start: float, stop: float, step: float, extras: Optional[List[float]] = None):
    if stop <= start or step <= 0:
        steps = [start]
    else:
        steps = [start + i * step for i in range(int((stop - start) / step + 1))]
    if extras:
        steps += extras
    return steps
