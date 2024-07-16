import math

class BinarySearchController():

    def __init__(self, outputRange = [0, 1], 
                       initialStepPercent: float = 10, 
                       initialOutput: float = 0.0, 
                       setPoint: float = 0.5,
                       tolerance: float = 0.01,
                       maxIter: int = 30) -> None:
        self.outputRange = outputRange
        self.initialStepPercent = initialStepPercent
        self.initialOutput = initialOutput
        self.setPoint = setPoint
        self.tolerance = tolerance
        self.maxIter = maxIter
        self.reset()

    def reset(self) -> None:
        self.iter = 0
        self.sign = 0
        self.lastSign = 0
        self.success = False
        self.fail = False
        self.outputRange.sort()
        self.output = self.initialOutput
        self.step = (self.initialStepPercent / 100) * abs(self.outputRange[1] - self.outputRange[0])
        self.setPointMin = self.setPoint - self.tolerance
        self.setPointMax = self.setPoint + self.tolerance

    def process(self, input) -> float:
        if self.setPointMin <= input <= self.setPointMax:
            self.success = True
            return self.output
        if self.iter > self.maxIter:
            self.fail = True
            return self.output

        self.iter += 1
        error = self.setPoint - input
        self.sign = math.copysign(1, error)

        if self.lastSign != 0 and self.sign != self.lastSign:
            self.step /= 2
        self.lastSign = self.sign

        self.output += self.sign * self.step
        self.output = min(max(self.output, self.outputRange[0]), self.outputRange[1])

        return self.output
         
    def isComplete(self):
        return self.success or self.fail
