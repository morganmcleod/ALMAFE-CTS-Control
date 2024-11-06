import yaml
from .schemas import Settings

class SettingsContainer():

    AMP_STABILITY_SETTINGS_FILE = "Settings/Settings_AmpStability.yaml"
    PHASE_STABILITY_SETTINGS_FILE = "Settings/Settings_PhaseStability.yaml"

    def __init__(self):
        self.loadSettingsAmpStability()
        self.loadSettingsPhaseStability()

    def loadSettingsAmpStability(self):
        try:
            with open(self.AMP_STABILITY_SETTINGS_FILE, "r") as f:
                d = yaml.safe_load(f)
                self.ampStability = Settings.model_validate(d)
        except:
            self.defaultSettingsAmpStability()

    def loadSettingsPhaseStability(self):
        try:
            with open(self.PHASE_STABILITY_SETTINGS_FILE, "r") as f:
                d = yaml.safe_load(f)
                self.phaseStability = Settings.model_validate(d)
        except:
            self.defaultSettingsPhaseStability()

    def defaultSettingsAmpStability(self):
        self.ampStability = Settings()
        self.saveSettingsAmpStability()

    def defaultSettingsPhaseStability(self):
        self.phaseStability = Settings()
        self.phaseStability.sampleRate = 5
        self.phaseStability.attenuateIF = 22
        self.saveSettingsPhaseStability()

    def saveSettingsAmpStability(self):
        with open(self.AMP_STABILITY_SETTINGS_FILE, "w") as f:
            yaml.dump(self.ampStability.model_dump(), f)

    def saveSettingsPhaseStability(self):
        with open(self.PHASE_STABILITY_SETTINGS_FILE, "w") as f:
            yaml.dump(self.phaseStability.model_dump(), f)
