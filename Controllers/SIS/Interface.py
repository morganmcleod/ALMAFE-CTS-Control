from abc import ABC, abstractmethod
from Measure.Shared.SelectSIS import SelectSIS
from Measure.MixerTests import ResultsQueue
from Measure.MixerTests.ResultsInterface import ResultsInterface
from AMB.schemas.MixerTests import IVCurveSettings
from AMB.CCADevice import IFPowerInterface

class SISBias_Interface(ABC):
   
    @abstractmethod
    def reset(self):
        """Reset to just constructed state.
        """
        pass

    @abstractmethod
    def read_bias(self, 
            select: SelectSIS, 
            numsamples: int = 10,
            stderr: list[float] = [None, None]
        ) -> tuple[float, float]:
        """Read and average a number of Vj, Ij samples

        :param SelectSIS select: Which bias circuit to read
        :param int numsamples: to be averaged, defaults to 100
        :param list[float] stderr: returns the standard error of the samples
        :return tuple[float, float]: averaged Vj, Ij
        """
        pass

    @abstractmethod
    def get_last_read(self, select: SelectSIS) -> tuple[float, float]:
        """Return the most recent bias reading.  For monitoring AutoLOPower progress        
        """
        pass

    @abstractmethod
    def read_bias_waveforms(self, 
            select: SelectSIS, 
            sample_rate: float, 
            numsamples: int = -1
        ) -> tuple[list[float], list[float]]:
        """Read and return a number of Vj, Ij samples

        :param SelectSIS select: Which bias circuit to read
        :param float sample_rate: Samples per second
        :param int numsamples: How many to read, defaults to -1
        :return tuple[list[float], list[float]]: VJ, IJ samples
        """
        pass

    @abstractmethod
    def measure_offsets(self, 
            enableSIS1: bool = True,
            enableSIS2: bool = True
        ) -> None:
        """Measure the voltage setting offsets for both mixers

        :side-effect updates self.offsets, sets both bias to 0.
        """
        pass

    @abstractmethod
    def set_bias(self,
            select: SelectSIS,
            bias_mV: float,
            use_offset: bool = False
        ) -> None:
        """Set the bias voltage

        :param SelectSIS select: Which bias circuit
        :param float bias_mV: to set
        :param bool use_offset: apply the previously measured offsets when setting, defaults to False
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def iv_curve(self, 
            select: SelectSIS,
            settings: IVCurveSettings, 
            resultsTarget: ResultsInterface,
            ifPowerDetect: IFPowerInterface | None = None,
            isPCold: bool = False
        ) -> None:
        pass