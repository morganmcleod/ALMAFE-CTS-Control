import logging
import threading
import yaml

from pydantic import BaseModel

from DebugOptions import *
from Controllers.schemas.DeviceInfo import DeviceInfo
from Controllers.IFSystem.Interface import IFSystem_Interface
from Controllers.SIS.Interface import SISBias_Interface, ResultsInterface, SelectSIS
from Controllers.LNA.Interface import LNABias_Interface, SelectLNA
from Controllers.LO.Interface import LOControl_Interface, LOSettings
from Controllers.Magnet.Interface import SISMagnet_Interface, ResultsInterface
from Measure.MixerTests import ResultsQueue
from Measure.Shared.SelectPolarization import SelectPolarization
from INSTR.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from INSTR.Chopper.Interface import Chopper_Interface
from AMB.schemas.MixerTests import *
from AMB.CCADevice import IFPowerInterface

from app_Common.CTSDB import CTSDB
from DBBand6Cart.MixerConfigs import MixerConfigs
from DBBand6Cart.MixerParams import MixerParams, MixerParam
from DBBand6Cart.PreampParams import PreampParams, PreampParam
from INSTR.SignalGenerator.Interface import SignalGenInterface
from .Interface import Receiver_Interface, AutoLOStatus

class MixerAssemblySettings(BaseModel):
    serialNum: str = ""
    min_percent: int = 15
    max_percent: int = 100    
    max_iter: int = 15
    tolerance: float = 0.5   # uA
    sleep: float = 0.2
    freqLOGHz: float = 0
    ytoLowGHz: float = 12.22
    ytoHighGHz: float = 14.77
    paGateVoltage: float = 0.05
    paPolarization: int = 0
    loSettings: LOSettings = LOSettings(refAmplitude = 5, setReference = True)
    
class MixerAssembly(Receiver_Interface):
    MIXERASSEMBLY_SETTINGS = "Settings/Settings_MixerAssembly.yaml"

    def __init__(self, 
            sisBias: SISBias_Interface, 
            sisMagnet: SISMagnet_Interface,
            loControl: LOControl_Interface,
            lnaBias: LNABias_Interface,
            temperatureMonitor: TemperatureMonitor
        ):
        self.logger = logging.getLogger("ALMAFE-CTS-Control")
        self.sisBias = sisBias
        self.sisMagnet = sisMagnet
        self.loControl = loControl
        self.lnaBias = lnaBias
        self.temperatureMonitor = temperatureMonitor
        self.reset()
        self.loadSettings()
        self.loControl.loDevice.setYTOLimits(self.settings.ytoLowGHz, self.settings.ytoHighGHz)
        
    def reset(self):
        self.configId = self.keys = None
        self.mixerParam1 = None
        self.mixerParam2 = None
        self.mixerParams1 = None
        self.mixerParams2 = None
        self.preampParam1 = None
        self.preampParam2 = None
        self.preampParams1 = None
        self.preampParams2 = None

    def loadSettings(self):
        try:
            with open(self.MIXERASSEMBLY_SETTINGS, "r") as f:
                d = yaml.safe_load(f)
                self.settings = MixerAssemblySettings.model_validate(d)
                if self.settings.serialNum:
                    DB = MixerConfigs(driver = CTSDB())
                    configs = DB.read(serialNum = self.settings.serialNum, latestOnly = True)
                    if configs:                    
                        self.setConfig(configs[0].key)
                    self.setBias(self.settings.freqLOGHz)
        except Exception as e:
            self.settings = MixerAssemblySettings()
            self.saveSettings()
    
    def saveSettings(self):
        try:
            with open(self.MIXERASSEMBLY_SETTINGS, "w") as f:
                yaml.dump(self.settings.model_dump(), f)
        except Exception as e:
            pass

    def getDeviceInfo(self) -> DeviceInfo:
        ret = self.loControl.getDeviceInfo()
        ret.name = "MixerAssembly"
        return ret

    def setConfig(self, configId:int) -> tuple[bool, str]:
        DB = MixerConfigs(driver = CTSDB())
        self.reset()
        self.settings = MixerAssemblySettings()
        if configId == 0:
            self.saveSettings()
            return True, ""
        configs = DB.read(keyMxrPreampAssys = configId)
        if not configs:
            return False, f"MixerAssembly: configId {configId} not found."
        self.settings.serialNum = configs[0].serialNum
        self.saveSettings()
        
        self.keys = DB.readKeys(configId)
        if self.keys:
            self.configId = configId
        else:
            return False, f"MixerAssembly: configId {configId} readKeys failed."

        if self.keys:
            DB = MixerParams(driver = CTSDB())
            self.mixerParams1 = DB.read(self.keys.keyChip1) if self.keys.keyChip1 else None
            self.mixerParams2 = DB.read(self.keys.keyChip2) if self.keys.keyChip2 else None
            DB = PreampParams(driver = CTSDB())
            self.preampParams1 = DB.read(self.keys.keyPreamp1) if self.keys.keyPreamp1 else None
            self.preampParams2 = DB.read(self.keys.keyPreamp2) if self.keys.keyPreamp2 else None
        return True, ""

    def getConfig(self) -> int:
        return self.configId if self.configId else 0

    def is2SB(self) -> bool:
        try:
            return self.keys.keyChip2 > 0
        except:
            return False

    def getPLL(self) -> dict:
        return self.loControl.getPLL()

    def getPA(self) -> dict:
        return self.loControl.getPA()

    def setBias(self, FreqLO:float, magnetOnly: bool = False) -> tuple[bool, str]:
        if not self.configId:
            return False, "MixerAssembly.setBias: no configuration is selected."
        self.settings.freqLOGHz = FreqLO
        self.saveSettings()
        DB = MixerParams(driver = CTSDB())
        if self.mixerParams1:
            self.mixerParam1 = DB.interpolate(FreqLO, self.mixerParams1)
            self.sisMagnet.setCurrent(self.mixerParam1.IMAG, SelectSIS.SIS1)
            if not magnetOnly:
                self.sisBias.set_bias(SelectSIS.SIS1, self.mixerParam1.VJ)
        if self.mixerParams2:
            self.mixerParam2 = DB.interpolate(FreqLO, self.mixerParams2)
            self.sisMagnet.setCurrent(self.mixerParam2.IMAG, SelectSIS.SIS2)
            if not magnetOnly:
                self.sisBias.set_bias(SelectSIS.SIS2, self.mixerParam2.VJ)
        
        if not magnetOnly:
            if self.preampParams1:
                self.lnaBias.set_bias(SelectLNA.LNA1, self.preampParams1[0])
                self.lnaBias.set_enable(SelectLNA.LNA1, True)
            if self.preampParams2:
                self.lnaBias.set_bias(SelectLNA.LNA2, self.preampParams2[0])
                self.lnaBias.set_enable(SelectLNA.LNA2, True)            
        return True, ""

    def setSISbias(self,
            select: SelectSIS,
            bias_mV: float,
            imag_mA: float = 0
        ) -> tuple[bool, str]:
        success = True
        msg = ""
        self.sisBias.set_bias(select, bias_mV, use_offset = True)
        if select == SelectSIS.SIS1:
            success, msg = self.sisMagnet.setCurrent(imag_mA)
        if not success:
            self.logger.error(msg)
            return False, msg
        else:
            return True, ""

    def readSISBias(self, select: SelectSIS, **kwargs) -> dict:
        averaging = kwargs.get('averaging', 1)        
        Vj, Ij = self.sisBias.read_bias(select, averaging)
        IMag = self.sisMagnet.readCurrent()
        return {
            'Vj': Vj,
            'Ij': Ij,
            'Imag': IMag if select == SelectSIS.SIS1 else 0,
            'averaging': averaging
        }

    def getLastSISRead(self, select: SelectSIS) -> dict:
        Vj, Ij = self.sisBias.get_last_read(select)
        return {
            'Vj': Vj if Vj else 0,
            'Ij': Ij if Ij else 0
        }
    
    def setPAOutput(self, pol: SelectPolarization, percent: float) -> None:
        self.loControl.setOutputPower(percent)

    def getPAOutput(self, pol: SelectPolarization) -> float:
        if pol == SelectPolarization.POL0:
            return self.loControl.getOuputPower()
        else:
            return 0
    
    def autoLOPower(self,             
            reinitialize: bool = False, 
            **kwargs
        ) -> tuple[bool, str]:

        if not kwargs.get('no_config', False) and not self.configId:
            return False, "MixerAssembly.autoLOPower: no configuration is selected."
       
        if SIMULATE:
            return True, ""

        targetIJ = kwargs.get('targetIJ', None)

        if kwargs.get('on_thread', False):
            threading.Thread(target = self._autoLOPower, args = (targetIJ, reinitialize), daemon = True).start()
            return True, ""
        else:
            return self._autoLOPower(targetIJ, reinitialize)

    def _autoLOPower(self, 
            targetIJ = None,
            reinitialize: bool = False
        ) -> tuple[bool, str]:

        if targetIJ is None:
            try:
                targetIJ = abs(self.mixerParam1.IJ)
            except:
                return False, "MixerAssembly._autoLOPower bias not available"
        
        self.logger.info(f"MixerAssembly._autoLOPower: target Ij = {targetIJ}")
        success, msg = self.loControl.autoLOPower(self.sisBias, targetIJ, reinitialize)
        return success, msg
    
    def getAutoLOStatus(self) -> AutoLOStatus:
        return self.loControl.getAutoLOStatus()

    def getTargetMixersBias(self, freqLO: float = None) -> tuple[MixerParam | None]:
        if not self.configId:
            self.logger.error("MixerAssembly.getTargetMixersBias: no configuration is selected.")
            return None, None
        if freqLO is not None:
            DB = MixerParams(driver = CTSDB())
            return (DB.interpolate(freqLO, self.mixerParams1), DB.interpolate(freqLO, self.mixerParams2))
        else:
            return (self.mixerParam1, self.mixerParam2)

    def setFrequency(self, 
            freqGHz: float, 
            settings: LOSettings
        ) -> tuple[bool, str]:
        return self.loControl.setFrequency(freqGHz, settings)

    def isLocked(self) -> bool:
        data = self.loControl.getPLL()
        return data['isLocked']

    def stop(self) -> None:
        self.sisBias.stop()
        self.sisMagnet.stop()

    def ivCurve(self, 
            settings: IVCurveSettings, 
            resultsTarget: ResultsInterface,
            ifPowerDetect: IFPowerInterface | None = None,
            ifSystem: IFSystem_Interface | None = None,
            chopper: Chopper_Interface | None = None
        ) -> tuple[bool, str]:
        self.sisBias.measure_offsets(settings.enable01, settings.enable02)

        if settings.measurePHot and chopper is not None:
            chopper.gotoHot()
        
        self._ivCurve(settings, resultsTarget, ifPowerDetect, ifSystem, isPCold = False)

        if settings.measurePCold and chopper is not None:
            chopper.gotoCold()
            self._ivCurve(settings, resultsTarget, ifPowerDetect, ifSystem, isPCold = True)

        resultsTarget.put(0, 1, IVCurvePoint(), ResultsQueue.PointType.ALL_DONE)
    
    def _ivCurve(self,
            settings: IVCurveSettings, 
            resultsTarget: ResultsInterface,
            ifPowerDetect: IFPowerInterface | None = None,
            ifSystem: IFSystem_Interface | None = None,
            isPCold: bool = False
        ) -> None:
        # set the selected IF output for measuring power
        if ifSystem is not None:
            ifSystem.set_pol_sideband(sideband = settings.measureSideband)
        # set the normal mixer bias for the current LO frequency:
        self.setBias(self.settings.freqLOGHz)        
        if settings.enable01:
            # turn off the opposite mixer's LNA:
            self.lnaBias.set_enable(SelectLNA.LNA1, True)
            self.lnaBias.set_enable(SelectLNA.LNA2, False)
            self.sisBias.iv_curve(SelectSIS.SIS1, settings, resultsTarget, ifPowerDetect, isPCold)
            self.lnaBias.set_enable(SelectLNA.LNA2, True)          
        if settings.enable02:
            # turn off the opposite mixer's LNA:
            self.lnaBias.set_enable(SelectLNA.LNA1, False)
            self.lnaBias.set_enable(SelectLNA.LNA2, True)
            self.sisBias.iv_curve(SelectSIS.SIS2, settings, resultsTarget, ifPowerDetect, isPCold)
            self.lnaBias.set_enable(SelectLNA.LNA1, True)

    def magnetOptimize(self, 
            settings: MagnetOptSettings, 
            resultsTarget: ResultsInterface
        ) -> tuple[bool, str]:
        return self.sisMagnet.magnetOptimize(settings, resultsTarget, self.sisBias)
    
    def mixersDeflux(self,
            settings: DefluxSettings,
            resultsTarget: ResultsInterface
        ) -> tuple[bool, str]:
        return self.sisMagnet.mixersDeflux(settings, resultsTarget)