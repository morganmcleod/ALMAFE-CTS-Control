import yaml
from AMB.schemas.MixerTests import IVCurveSettings, MagnetOptSettings, DefluxSettings

class SettingsContainer():
    SETTINGS_IV_CURVES = "Settings/Settings_IVCurves.yaml"
    SETTINGS_MAGNET_OPT = "Settings/Settings_MagnetOpt.yaml"
    SETTINGS_DEFLUX = "Settings/Settings_Deflux.yaml"

    def __init__(self):
        self.loadSettingsIVCurve()
        self.loadSettingsMagOpt()
        self.loadSettingsDeflux()

    def loadSettingsIVCurve(self):
        try:
            with open(self.SETTINGS_IV_CURVES, "r") as f:
                d = yaml.safe_load(f)
                self.ivCurveSettings = IVCurveSettings.model_validate(d)
        except:
            self.setDefaultsIVCurve()
    
    def setDefaultsIVCurve(self):
        self.ivCurveSettings = IVCurveSettings()
        self.saveSettingsIVCurve()

    def saveSettingsIVCurve(self):
        with open(self.SETTINGS_IV_CURVES, "w") as f:
            yaml.dump(self.ivCurveSettings.model_dump(), f)

    def loadSettingsMagOpt(self):
        try:
            with open(self.SETTINGS_MAGNET_OPT, "r") as f:
                d = yaml.safe_load(f)
                self.magnetOptSettings = MagnetOptSettings.model_validate(d)
        except:
            self.setDefaultsMagOpt()
    
    def setDefaultsMagOpt(self):
        self.magnetOptSettings = MagnetOptSettings()
        self.saveSettingsMagOpt()

    def saveSettingsMagOpt(self):
        with open(self.SETTINGS_MAGNET_OPT, "w") as f:
            yaml.dump(self.magnetOptSettings.model_dump(), f)

    def loadSettingsDeflux(self):
        try:
            with open(self.SETTINGS_DEFLUX, "r") as f:
                d = yaml.safe_load(f)
                self.defluxSettings = DefluxSettings.model_validate(d)
        except:
            self.setDefaultsDeflux()
    
    def setDefaultsDeflux(self):
        self.defluxSettings = DefluxSettings()
        self.saveSettingsDeflux()

    def saveSettingsDeflux(self):
        with open(self.SETTINGS_DEFLUX, "w") as f:
            yaml.dump(self.defluxSettings.model_dump(), f)