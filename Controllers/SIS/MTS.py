import logging
import nidaqmx
import time
import threading
from nidaqmx.constants import TerminalConfiguration, READ_ALL_AVAILABLE
from math import sqrt
from statistics import mean, stdev

import nidaqmx.constants
from .Interface import SelectSIS, SISBias_Interface, IFPowerInterface, ResultsInterface
from Measure.MixerTests import ResultsQueue
from AMB.schemas.MixerTests import IVCurvePoint, IVCurveSettings
from Measure.Shared.Sampler import Sampler

class SISBias(SISBias_Interface):
    """MTS SIS bias control via NI-DAQ, both MTS-1 and MTS-2
    """
    def __init__(self, simulate: bool = False):
        """Constructor

        :param bool simulate, defaults to False
        """
        self.logger = logging.getLogger("ALMAFE-Instr")
        self.logger.info(f"MTS SIS Bias created")
        self.simulate = simulate
        self.setBiasTasks: dict[SelectSIS, nidaqmx.Task] = {
            SelectSIS.SIS1: None,
            SelectSIS.SIS2: None
        }
        self.readBiasTasks:  dict[SelectSIS, nidaqmx.Task] = {
            SelectSIS.SIS1: None,
            SelectSIS.SIS2: None
        }
        self.readBiasLocks: dict[SelectSIS, threading.Lock] = {
            SelectSIS.SIS1: threading.Lock(),
            SelectSIS.SIS2: threading.Lock()
        }

        if not simulate:
            try:                
                self.setBiasTasks[SelectSIS.SIS1] = nidaqmx.Task("SetV1")
                self.setBiasTasks[SelectSIS.SIS1].ao_channels.add_ao_voltage_chan("Dev1/ao0")
            except Exception as e:
                print(1, e)
            
            try:                
                self.setBiasTasks[SelectSIS.SIS2] = nidaqmx.Task("SetV2")
                self.setBiasTasks[SelectSIS.SIS2].ao_channels.add_ao_voltage_chan("Dev1/ao1")
            except Exception as e:
                print(2, e)
            
            try:
                self.readBiasTasks[SelectSIS.SIS1] = nidaqmx.Task("ReadIV1")
                self.readBiasTasks[SelectSIS.SIS1].ai_channels.add_ai_voltage_chan("Dev1/ai0", terminal_config = TerminalConfiguration.RSE)
                self.readBiasTasks[SelectSIS.SIS1].ai_channels.add_ai_voltage_chan("Dev1/ai1", terminal_config = TerminalConfiguration.RSE)
            except Exception as e:
                print(3, e)

            try:
                self.readBiasTasks[SelectSIS.SIS2] = nidaqmx.Task("ReadIV2")
                self.readBiasTasks[SelectSIS.SIS2].ai_channels.add_ai_voltage_chan("Dev1/ai2", terminal_config = TerminalConfiguration.RSE)
                self.readBiasTasks[SelectSIS.SIS2].ai_channels.add_ai_voltage_chan("Dev1/ai3", terminal_config = TerminalConfiguration.RSE)
            except Exception as e:
                print(4, e)

        self.reset()

    def __del__(self):
        """Destructor closes tasks.
        """
        if not self.simulate:
            if self.setBiasTasks[SelectSIS.SIS1]:
                self.setBiasTasks[SelectSIS.SIS1].close()
            if self.setBiasTasks[SelectSIS.SIS2]:
                self.setBiasTasks[SelectSIS.SIS2].close()
            if self.readBiasTasks[SelectSIS.SIS1]:
                self.readBiasTasks[SelectSIS.SIS1].close()
            if self.readBiasTasks[SelectSIS.SIS2]:
                self.readBiasTasks[SelectSIS.SIS2].close()

    def reset(self):
        """Reset to just constructed state.
        """
        self.offsets = {
            SelectSIS.SIS1: 0,
            SelectSIS.SIS2: 0
        }
        self.setVoltages = {
            SelectSIS.SIS1: 0,
            SelectSIS.SIS2: 0
        }
        self.lastRead = {
            SelectSIS.SIS1: (0, 0),
            SelectSIS.SIS2: (0, 0),
        }
        self.stopNow = False

    def read_bias(self, 
            select: SelectSIS, 
            numsamples: int = 100,
            stderr: list[float] = [None, None]
        ) -> tuple[float, float]:
        """Read and average a number of Vj, Ij samples

        :param SelectSIS select: Which bias circuit to read
        :param int numsamples: to be averaged, defaults to 100
        :param list[float] stderr: returns the standard error of the samples
        :return tuple[float, float]: averaged Vj, Ij
        """
        VJ, IJ = self.read_bias_waveforms(select, 600, numsamples)
        if VJ and IJ:
            stderr[0] = stdev(VJ) / sqrt(numsamples)
            stderr[1] = stdev(IJ) / sqrt(numsamples)
            self.lastRead[select] = (mean(VJ), mean(IJ))
            return self.lastRead[select]
        else:
            return 0, 0

    def get_last_read(self, select: SelectSIS) -> tuple[float, float]:
        return self.lastRead[select]

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
        if self.simulate:
            return [0] * numsamples, [0] * numsamples
        
        self.readBiasLocks[select].acquire()
        task = self.readBiasTasks[select]
        task.timing.cfg_samp_clk_timing(
            sample_rate,
            sample_mode = nidaqmx.constants.AcquisitionType.FINITE,
            samps_per_chan = numsamples if numsamples > 1 else 2  #2 is minimum legal value
        )
        try:
            IJ, VJ = task.read(
                number_of_samples_per_channel = READ_ALL_AVAILABLE,
                timeout = numsamples / sample_rate + 0.1
            )
        except Exception as e:
            self.logger.exception(e)
            return None, None
        finally:
            self.readBiasLocks[select].release()
        # convert to mV, uA
        VJ = [10 * x for x in VJ]
        IJ = [100 * x for x in IJ]
        return VJ, IJ

    def measure_offsets(self,
            enableSIS1: bool = True,
            enableSIS2: bool = True
        ) -> None:
        """Measure the voltage setting offsets for both mixers

        :side-effect updates self.offsets, sets both bias to 0.
        """
        self.offsets = {
            SelectSIS.SIS1: 0,
            SelectSIS.SIS2: 0
        }
        if not self.simulate:
            if enableSIS1:
                self.set_bias(SelectSIS.SIS1, -8.5)
                time.sleep(0.2)
                vj, _ = self.read_bias(SelectSIS.SIS1)
                self.offsets[SelectSIS.SIS1] = -8.5 - vj
                self.set_bias(SelectSIS.SIS1, 0)
            
            if enableSIS2:
                self.set_bias(SelectSIS.SIS2, 8.5)
                time.sleep(0.2)
                vj, _ = self.read_bias(SelectSIS.SIS2)
                self.offsets[SelectSIS.SIS2] = 8.5 - vj
                self.set_bias(SelectSIS.SIS2, 0)
        self.logger.info(f"SISBias.measure_offsets: SIS1={self.offsets[SelectSIS.SIS1]:.6f} mV, SIS2={self.offsets[SelectSIS.SIS2]:.6f} mV")

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
        if self.simulate:
            return
        if select.testSis(1):
            self._set_bias(SelectSIS.SIS1, bias_mV, use_offset)
        if select.testSis(2):
            self._set_bias(SelectSIS.SIS2, bias_mV, use_offset)

    def _set_bias(self, 
            select: SelectSIS, 
            bias_mV: float,
            use_offset: bool = False
        ) -> None:
        task = self.setBiasTasks[select]
        offset = self.offsets[select]
        self.setVoltages[select] = bias_mV
        task.write((bias_mV + (offset if use_offset else 0)) / 10)

    def stop(self) -> None:
        self.stopNow = True

    def iv_curve(self, 
            select: SelectSIS,
            settings: IVCurveSettings, 
            resultsTarget: ResultsInterface,
            ifPowerDetect: IFPowerInterface | None = None,
            isPCold: bool = False
        ) -> None:

        self.stopNow = False
        settings.sort()
        success, msg = settings.is_valid()
        if not success:
            self.logger.error(f"SISBias.iv_curve: {msg}")
            return

        # measure IF power is only supported when 'interactive':
        if settings.measurePHot or settings.measurePCold:
            settings.interactive = True

        vjStart = settings.vjStart
        vjStop = settings.vjStop
        # make vjStep positive for now:
        vjStep = abs(settings.vjStep)

        # prevent divide by zero:
        VjRange = vjStop - vjStart
        if VjRange == 0:
            self.logger.error(f"SISBias.iv_curve: {vjStart}=={vjStop} would divide by zero.")
            return
        
        # check that VjRange is at least 1 step
        elif VjRange < vjStep:
            self.logger.error(f"SISBias.iv_curve: {vjStart}..{vjStop} is smaller than one step.")
            return

        # Sweep one or two ranges:
        Vj1Negative = vjStart < 0
        Vj2Positive = vjStop > 0
        zeroCrossing = Vj1Negative and Vj2Positive

        # store the voltage setting in effect now:
        priorState1 = self.setVoltages[SelectSIS.SIS1]
        priorState2 = self.setVoltages[SelectSIS.SIS2]

        # turn off the other SIS:
        self.set_bias(SelectSIS(3 - select.value), 0)

        # send a point to indicate beginning of a curve:
        resultsTarget.put(0, select.value, IVCurvePoint(isPCold = isPCold), ResultsQueue.PointType.START)

        # Sweep first range from negative towards zero:
        if Vj1Negative and not self.stopNow:
            endpt = 0 if zeroCrossing else vjStop
            if not settings.interactive:
                self._iv_curve_inner_loop_fast(
                    select, 
                    vjStart, 
                    endpt, 
                    vjStep, 
                    resultsTarget
                )
            else:
                self._iv_curve_inner_loop_interactive(
                    select, 
                    vjStart, 
                    endpt, 
                    vjStep, 
                    ifPowerDetect if settings.measurePHot else None, 
                    resultsTarget,
                    isPCold
                )

        # insert a null at the zero crossing so that the graph won't have a jump:
        if zeroCrossing:
            resultsTarget.put(0, select.value, IVCurvePoint(isPCold = isPCold), ResultsQueue.PointType.GAP)
        
        # Sweep second range from positive towards zero:
        if Vj2Positive and not self.stopNow:
            endpt = 0 if zeroCrossing else vjStart
            if not settings.interactive:
                self._iv_curve_inner_loop_fast(
                    select, 
                    vjStop, 
                    endpt, 
                    -vjStep, 
                    resultsTarget
                )
            else:
                self._iv_curve_inner_loop_interactive(
                    select, 
                    vjStop, 
                    endpt, 
                    -vjStep, 
                    ifPowerDetect if settings.measurePHot else None, 
                    resultsTarget,
                    isPCold
                )
        
        # send a point to indicate end of a curve:
        resultsTarget.put(0, select.value, IVCurvePoint(isPCold = isPCold), ResultsQueue.PointType.END)
        
        # restore prior state
        self.set_bias(SelectSIS.SIS1, priorState1)
        self.set_bias(SelectSIS.SIS2, priorState2)

    def _iv_curve_inner_loop_fast(self,             
            select: SelectSIS,
            vj1: float, 
            vj2: float, 
            vjStep: float,
            resultsTarget: ResultsInterface
        ) -> None:

        # sweep to the first point:
        self.set_bias(select, vj1)
        time.sleep(0.2)

        vjSet = vj1
        VJSet = []

        sample_rate = 1000
        averaging = 40
        dt_step = 1 / sample_rate * averaging
        num_steps = int(abs((vj2 - vj1) / vjStep))
        num_pts = num_steps + 1
        num_samples = averaging * num_pts
        total_time = num_samples / sample_rate
        self.logger.info(f"SISBias._iv_curve_innner_loop_fast: will take {total_time} s")

        def step():
            nonlocal vjSet, VJSet
            self.set_bias(select, vjSet, use_offset = True)            
            VJSet.append(vjSet)
            vjSet += vjStep

        # stepper is a Sampler which runs a loop on a worker thread:
        stepper = Sampler(dt_step, step)
        stepper.start()

        # read bias on this thread:
        VJ, IJ = self.read_bias_waveforms(select, sample_rate, num_samples)
        stepper.stop()
        
        # Average by oversampling, drop first N samples from each box:
        VJ = self._boxcar_average(VJ, averaging)
        IJ = self._boxcar_average(IJ, averaging)
        # Trim any extra values in VJSet and IFPower, due to race between read_bias_waveforms() and sampler.stop() above
        VJSet = VJSet[:len(VJ)]

        if vjStep < 0:
            # reverse the results when stepping in negative direction so that VjSet increases monotonically:            
            VJSet.reverse()
            VJ.reverse()
            IJ.reverse()

        points = [
            IVCurvePoint(
                pol = 0,
                sis = select.value,
                vjSet = vjSet,
                vjRead = vjRead,
                ijRead = ijRead
            )
            for vjSet, vjRead, ijRead in zip(VJSet, VJ, IJ)
        ]
        resultsTarget.put(0, select.value, points)

    def _iv_curve_inner_loop_interactive(self,             
            select: SelectSIS,
            vj1: float, 
            vj2: float, 
            vjStep: float, 
            ifPowerDetect: IFPowerInterface | None,
            resultsTarget: ResultsInterface,
            isPCold: bool = False
        ) -> None:

        averaging = 25

        # sweep to the first point:
        self.set_bias(select, vj1)
        time.sleep(0.2)

        vjSet = vj1
        done = False
                
        while not done and not self.stopNow:
            self.set_bias(select, vjSet, use_offset = True)
            time.sleep(0.01)
            vjRead, ijRead = self.read_bias(select, averaging)
            resultsTarget.put(
                0,
                select.value,
                IVCurvePoint(
                    vjSet = vjSet,
                    vjRead = vjRead,
                    ijRead = ijRead,
                    ifPower = ifPowerDetect.read() if ifPowerDetect else None,
                    isPCold = isPCold
                )
            )
            vjSet += vjStep
            if vjStep < 0 and vjSet < vj2 + vjStep:
                done = True
            elif vjStep > 0 and vjSet > vj2 + vjStep:
                done = True

    def _boxcar_average(self, A, K):
        '''
        returns boxcar-averaged array B from A, where each element of B
        contains the mean over non-overlapping groups of K samples of A.
        '''    
        B = []
        # N is the size of the input data array:
        N = len(A)
        # K is the number of points to group and average:
        K = int(K)
        if K < 1:
            K = 1
        if K > N:
            K = N
        # M is number of groups:
        M = N // K
        for i in range(M):
            i0 = i * K
            B.append(sum(A[i0 : i0 + K]) / K)
        return B
