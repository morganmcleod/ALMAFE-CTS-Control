import bisect
import logging
from sys import float_info
from statistics import mean

logger = logging.getLogger("ALMAFE-CTS-Control")

class BinaryProbabilityDistribution():
    def __init__(self, min: float, max: float):
        self.pdf = [1.0]
        self.limits = [min, max]

    def split_at(self, x:float, leftp: float, rightp: float) -> None:
        # insert the new value in-order the limits list:
        pos = bisect.bisect_left(self.limits, x)
        self.limits.insert(pos, x)
        # clone the PDF value below the insertion point:
        self.pdf.insert(pos - 1, self.pdf[pos - 1])
        # apply new weights above and below the insertion point:
        for i in range(len(self.pdf)):
            if i < pos:
                self.pdf[i] *= leftp
            else:
                self.pdf[i] *= rightp
        

    def find_median(self) -> float:
        # calculate the area under each partition of the PDF
        integral = [0] * len(self.limits)
        sum = 0
        for i in range(1, len(self.limits)):
            integral[i] = (self.limits[i] - self.limits[i - 1]) * self.pdf[i - 1]
            sum += integral[i]
        # calculate the cumulative probability distribution
        cumSum = 0
        cpdf = [0] * len(self.limits)
        for i in range(1, len(integral)):
            cumSum += integral[i]
            cpdf[i] = cumSum / sum
        # evaluate cpdf at the point x=0.5 with linear interpolation
        i = bisect.bisect_left(cpdf, 0.5)
        x_lower = cpdf[i - 1]
        y_lower = self.limits[i - 1]
        x_upper = cpdf[i]
        y_upper = self.limits[i]
        slope = (y_upper - y_lower) / (x_upper - x_lower)
        y_int = y_lower - slope * x_lower
        return y_int + slope * 0.5


class PBAController():
    """Probablistic Bisection Algorithm"""

    def __init__(self, 
            setpoint:float = 0.5,
            tolerance: float = 0.5,
            output_limits: tuple[float] = (0, 1),
            min_resolution: float = 0.0005,
            max_iter: int = 10):
        self.setpoint = setpoint
        self.tolerance = tolerance
        self.output_limits = output_limits
        self.min_resolution = min_resolution
        self.max_iter = max_iter
        self.reset()

    def reset(self):
        self.p = 0.65
        self.q = 1 - self.p
        self.pdf = BinaryProbabilityDistribution(self.output_limits[0], self.output_limits[1])
        self.error = float_info.max
        self.best_error = self.error
        self.output = (self.output_limits[0] + self.output_limits[1]) / 2
        self.best_output = self.output
        self.output = self.best_output
        self.last_errors = []
        self.iter = 0
        self.done = False
        self.fail = False

    def process(self, current_value: float) -> float:
        if self.done:
            return self.output
        self.error = current_value - self.setpoint
        self.error = current_value - self.setpoint
        if self.error < self.best_error:
            self.best_error = self.error
            self.best_output = self.output
        self.error = current_value - self.setpoint        
        if self.error < self.best_error:
            self.best_error = self.error
            self.best_output = self.output
        self.last_errors.append(self.error)
        while len(self.last_errors) > 6:
            self.last_errors.pop(0)
        if abs(self.error) < self.tolerance:
            logger.debug("PBAController.process done: abs(error) < tolerance")
            self.done = True
        # if the average of the last 6 values are less than the tolerance
        # we are likely bouncing between values on either side of the
        # target, and can confidently break out early.
        elif self.iter > self.max_iter:
            if abs(mean(self.last_errors)) < self.tolerance:
                logger.debug(f"PBAController.process done: over {self.max_iter} iterations and mean errors < tolerance")
                self.done = True
            else:
                logger.debug(f"PBAController.process failed to converge in {self.max_iter} iterations.")
                self.done = True
                self.fail = True            
        else:
            leftp = 2 * self.p
            rightp = 2 * self.q
            if self.error < 0:
                leftp, rightp = rightp, leftp
            self.pdf.split_at(self.output, leftp, rightp)
            result = self.pdf.find_median()
            # If the bisection becomes too small, we're done:
            if abs(result - self.output) < self.min_resolution:
                logger.debug("PBAController.process done: bisection size is below min_resolution")
                self.done = True
            self.output = result            

        # If not currently on the best output, set it back. This will prevent
        # settling on a worse result when the algorithm bounces between
        # two values on either side of the ideal.
        if self.done:
            if abs(self.error) > self.best_error:
                self.output = self.best_output
        elif self.error < self.best_error:
            self.best_error = self.error
            self.best_output = self.output
        logger.debug(f"PBAController.process: iter={self.iter} current_value={current_value} output={self.output} done={self.done} fail={self.fail}")
        self.iter += 1
        return self.output
