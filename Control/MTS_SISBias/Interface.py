from abc import ABC, abstractmethod
from enum import Enum

class SelectBias(Enum):
    SIS1 = 0
    SIS2 = 1

class SISBias_interface(ABC):
   
    @abstractmethod
    def reset(self):
        """Reset to just constructed state.
        """
        pass

    @abstractmethod
    def read_bias(self, 
            select: SelectBias, 
            numsamples: int = 100,
            stderr: list[float] = [None, None]
        ) -> tuple[float, float]:
        """Read and average a number of Vj, Ij samples

        :param SelectBias select: Which bias circuit to read
        :param int numsamples: to be averaged, defaults to 100
        :param list[float] stderr: returns the standard error of the samples
        :return tuple[float, float]: averaged Vj, Ij
        """
        pass

    @abstractmethod
    def read_bias_waveforms(self, 
            select: SelectBias, 
            sample_rate: float, 
            numsamples: int = -1
        ) -> tuple[list[float], list[float]]:
        """Read and return a number of Vj, Ij samples

        :param SelectBias select: Which bias circuit to read
        :param float sample_rate: Samples per second
        :param int numsamples: How many to read, defaults to -1
        :return tuple[list[float], list[float]]: VJ, IJ samples
        """
        pass

    @abstractmethod
    def measure_offsets(self) -> None:
        """Measure the voltage setting offsets for both mixers

        :side-effect updates self.offsets, sets both bias to 0.
        """
        pass

    @abstractmethod
    def set_bias(self,
            select: SelectBias,
            bias_mV: float,
            use_offset: bool = False
        ) -> None:
        """Set the bias voltage

        :param SelectBias select: Which bias circuit
        :param float bias_mV: to set
        :param bool use_offset: apply the previously measured offsets when setting, defaults to False
        """
        pass