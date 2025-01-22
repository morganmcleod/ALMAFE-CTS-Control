import logging
import nidaqmx
from enum import Enum
from math import sqrt
from statistics import mean, stdev
import nidaqmx.constants
from .Interface import SelectBias, SISBias_interface

class SISBias(SISBias_interface):
    """MTS SIS bias control via NI-DAQ
    """
    def __init__(self, simulate: bool = False):
        """Constructor

        :param bool simulate, defaults to False
        """
        self.logger = logging.getLogger("ALMAFE-Instr")
        self.logger.info(f"MTS SIS Bias created")
        self.simulate = simulate
        if not simulate: 
            self.setBiasTasks: list[nidaqmx.Task] = [None, None]
            self.setBiasTasks[0] = self._initTask("", "SET SIS1 V", isInput = False)
            self.setBiasTasks[1] = self._initTask("", "SET SIS2 V", isInput = False)
            self.setBiasTasks[0].start()
            self.setBiasTasks[1].start()

            self.readBiasTasks: list[nidaqmx.Task] = [None, None]
            self.readBiasTasks[0] = self._initTask("", "READ SIS1 IV", isInput = True)
            self.readBiasTasks[1] = self._initTask("", "READ SIS2 IV", isInput = True)
            self.readBiasTasks[0].start()
            self.readBiasTasks[1].start()
        self.reset()

    def _initTask(self, 
            lines: str, 
            name: str = "", 
            isInput: bool = 
        True) -> nidaqmx.Task | None:
        """Helper to initialize a nidaqmx.Task

        :param str lines: analog i/o lines to assign
        :param str name: to assign to the lines, defaults to ""
        :param bool isInput defaults to True
        :return nidaqmx.Task | None
        """
        def constructAssign(lines, name, isInput) -> nidaqmx.Task | None:
            try:
                task = nidaqmx.Task(name)
                if isInput:
                    task.ai_channels.add_ai_voltage_chan(lines, name)
                else:
                    task.ao_channels.add_ao_voltage_chan(lines, name)
                return task
            except:
                task = nidaqmx.Task(name)
                task.close()
                return None
        
        task = constructAssign(lines, name, isInput)
        if task is None:
            task = constructAssign(lines, name, isInput)
        return task
    
    def __del__(self):
        """Destructor closes tasks.
        """
        if not self.simulate:
            self.setBiasTasks[0].close()
            self.setBiasTasks[1].close()
            self.readBiasTasks[0].close()
            self.readBiasTasks[1].close()

    def reset(self):
        """Reset to just constructed state.
        """
        self.offsets = [0, 0]

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
        VJ, IJ = self.read_bias_waveforms(select, 600, numsamples)
        stderr[0] = stdev(VJ) / sqrt(numsamples)
        stderr[1] = stdev(IJ) / sqrt(numsamples)
        return mean(VJ), mean(IJ)

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
        if self.simulate:
            return [0] * numsamples, [0] * numsamples
        
        self.readBiasTasks[select.value].timing.cfg_samp_clk_timing(
            sample_rate,
            sample_mode = nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan = numsamples
        )
        IJ, VJ = self.readBiasTasks[select.value].read(
            numsamples, 
            timeout = numsamples / sample_rate + 0.1
        )
        VJ = [10 * x for x in VJ]
        IJ = [100 * x for x in IJ]
        return VJ, IJ

    def measure_offsets(self) -> None:
        """Measure the voltage setting offsets for both mixers

        :side-effect updates self.offsets, sets both bias to 0.
        """
        self.offsets = [0, 0]
        if not self.simulate:
            self.set_bias(SelectBias.SIS1, -8.0)
            vj, _ = self.read_bias(SelectBias.SIS1)
            self.offsets[0] = -8.0 - vj
            self.set_bias(SelectBias.SIS1, 0)        
            self.set_bias(SelectBias.SIS2, 8.0)
            vj, _ = self.read_bias(SelectBias.SIS2)
            self.offsets[1] = 8.0 - vj
            self.set_bias(SelectBias.SIS2, 0)

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
        if not self.simulate:
            self.setBiasTasks[select.value].write(bias_mV / 10 + self.offsets[select.value] if use_offset else 0)
