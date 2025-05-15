import yaml
from .schemas import *
from INSTR.SpectrumAnalyzer.schemas import SpectrumAnalyzerSettings

class SettingsContainer():
    COMMON_SETTINGS_FILE = "Settings/Settings_NTCommon.yaml"
    WARM_IF_SETTINGS_FILE = "Settings/Settings_WarmIF.yaml"
    NOISE_TEMP_SETTINGS_FILE = "Settings/Settings_NoiseTemp.yaml"
    LO_WG_INTEGRITY_SETTINGS_FILE = "Settings/Settings_LOWGIntegrity.yaml"
    BIAS_OPT_SETTINGS_FILE = "Settings/Settings_BiasOpt.yaml"
    YFACTOR_SETTINGS_FILE = "Settings/Settings_YFactor.yaml"
    NT_SPECAN_SETTINGS_FILE = "Settings/Settings_NTSpecAn.yaml"
    IR_SPECAN_SETTINGS_FILE = "Settings/Settings_IRSpecAn.yaml"

    def __init__(self):
        self.setDefaultTestSteps()
        self.loadSettings()

    def setDefaultTestSteps(self):
        self.testSteps = TestSteps()

    def loadSettings(self):
        self.loadSettingsCommon()
        self.loadSettingsWarmIF()
        self.loadSettingsNoiseTemp()
        self.loadSettingsLOWGIntegrity()
        self.loadSettingsBiasOpt()
        self.loadSettingsYFactor()
        self.loadSettingsNTSpecAn()
        self.loadSettingsIRSpecAn()

    def loadSettingsCommon(self):
        try:
            with open(self.COMMON_SETTINGS_FILE, "r") as f:
                d = yaml.safe_load(f)
                self.commonSettings = CommonSettings.model_validate(d)
        except:
            self.setDefaultsCommon()

    def setDefaultsCommon(self):
        self.commonSettings = CommonSettings()
        self.saveSettingsCommon()

    def saveSettingsCommon(self):
        with open(self.COMMON_SETTINGS_FILE, "w") as f:
            yaml.dump(self.commonSettings.model_dump(), f)

    def loadSettingsWarmIF(self):
        try:
            with open(self.WARM_IF_SETTINGS_FILE, "r") as f:
                d = yaml.safe_load(f)
                self.warmIFSettings = WarmIFSettings.model_validate(d)
        except:
            self.setDefaultsWarmIF()

    def setDefaultsWarmIF(self):
        self.warmIFSettings = WarmIFSettings()
        self.saveSettingsWarmIF()

    def saveSettingsWarmIF(self):
        with open(self.WARM_IF_SETTINGS_FILE, "w") as f:
            yaml.dump(self.warmIFSettings.model_dump(), f)

    def loadSettingsNoiseTemp(self):
        try:
            with open(self.NOISE_TEMP_SETTINGS_FILE, "r") as f:
                d = yaml.safe_load(f)
                self.noiseTempSettings = NoiseTempSettings.model_validate(d)
        except:
            self.setDefaultsNoiseTemp()

    def setDefaultsNoiseTemp(self):
        self.noiseTempSettings = NoiseTempSettings()
        self.saveSettingsNoiseTemp()

    def saveSettingsNoiseTemp(self):
        with open(self.NOISE_TEMP_SETTINGS_FILE, "w") as f:
            yaml.dump(self.noiseTempSettings.model_dump(), f)
        
    def loadSettingsLOWGIntegrity(self):
        try:
            with open(self.LO_WG_INTEGRITY_SETTINGS_FILE, "r") as f:
                d = yaml.safe_load(f)
                self.loWgIntegritySettings = NoiseTempSettings.model_validate(d)
        except:
            self.setDefaultsLOWGIntegrity()

    def setDefaultsLOWGIntegrity(self):
        self.loWgIntegritySettings = NoiseTempSettings(loStep = 0.1, ifStart = 6.0, ifStop = 6.0)
        self.saveSettingsLOWGIntegrity()

    def saveSettingsLOWGIntegrity(self):
        with open(self.LO_WG_INTEGRITY_SETTINGS_FILE, "w") as f:
            yaml.dump(self.loWgIntegritySettings.model_dump(), f)

    def loadSettingsBiasOpt(self):
        try:
            with open(self.BIAS_OPT_SETTINGS_FILE, "r") as f:
                d = yaml.safe_load(f)
                self.biasOptSettings = BiasOptSettings.model_validate(d)
        except:
            self.setDefaultsBiasOpt()

    def setDefaultsBiasOpt(self):
        self.biasOptSettings = BiasOptSettings()
        self.saveSettingsBiasOpt()

    def saveSettingsBiasOpt(self):
        with open(self.BIAS_OPT_SETTINGS_FILE, "w") as f:
            yaml.dump(self.biasOptSettings.model_dump(), f)

    def loadSettingsYFactor(self):
        try:
            with open(self.YFACTOR_SETTINGS_FILE, "r") as f:
                d = yaml.safe_load(f)
                self.yFactorSettings = YFactorSettings.model_validate(d)
        except Exception as e:
            self.setDefaultsYFactor()

    def setDefaultsYFactor(self):
        self.yFactorSettings = YFactorSettings()
        self.saveSettingsYFactor()

    def saveSettingsYFactor(self):
        with open(self.YFACTOR_SETTINGS_FILE, "w") as f:
            yaml.dump(self.yFactorSettings.model_dump(), f)

    def loadSettingsNTSpecAn(self):
        try:
            with open(self.NT_SPECAN_SETTINGS_FILE, "r") as f:
                d = yaml.safe_load(f)
                self.ntSpecAnSettings = SpectrumAnalyzerSettings.model_validate(d)
        except:
            self.setDefaultsNTSpecAn()

    def setDefaultsNTSpecAn(self):
        self.ntSpecAnSettings = SpectrumAnalyzerSettings(attenuation = 2, enableInternalPreamp = True)
        self.saveSettingsNTSpecAn()

    def saveSettingsNTSpecAn(self):
        with open(self.NT_SPECAN_SETTINGS_FILE, "w") as f:
            yaml.dump(self.ntSpecAnSettings.model_dump(), f)

    def loadSettingsIRSpecAn(self):
        try:
            with open(self.IR_SPECAN_SETTINGS_FILE, "r") as f:
                d = yaml.safe_load(f)
                self.irSpecAnSettings = SpectrumAnalyzerSettings.model_validate(d)
        except:
            self.setDefaultsIRSpecAn()

    def setDefaultsIRSpecAn(self):
        self.irSpecAnSettings = SpectrumAnalyzerSettings(
            attenuation = 16, 
            resolutionBW = 10e3,             
            enableInternalPreamp = True,
            sweepPoints = 201
        )        
        self.saveSettingsIRSpecAn()

    def saveSettingsIRSpecAn(self):
        with open(self.IR_SPECAN_SETTINGS_FILE, "w") as f:
            yaml.dump(self.irSpecAnSettings.model_dump(), f)
