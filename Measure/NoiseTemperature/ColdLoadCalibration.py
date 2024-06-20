
from CTSDevices.SpectrumAnalyzer.SpectrumAnalyzer import SpectrumAnalyzer, SpectrumAnalyzerSettings
from CTSDevices.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from openpyxl import Workbook
import threading
import yaml
import time
from datetime import datetime

class ColdLoadCalibration():

    COLDLLOAD_SPECAN_SETTINGS_FILE = "Settings_ColdLoadSpecAn.yaml"

    def __init__(self,
            spectrumAnalyzer: SpectrumAnalyzer,
            temperatureMonitor: TemperatureMonitor):
        self.spectrumAnalyzer = spectrumAnalyzer
        self.temperatureMonitor = temperatureMonitor
        self.specAnSettings = None
        self.reset()

    def reset(self):
        self.stopNow = False
        self.stopped = False
        self.paused = False
        self.ambSensorNum = 7
        self.tAmb = 0
        self.power = -100.0
        self.nextAnnotation = None
        self.wb = None
        self.loadSettingsSpecAn()
        self.spectrumAnalyzer.configureAll(self.specAnSettings)

    def loadSettingsSpecAn(self):
        try:
            with open(self.COLDLLOAD_SPECAN_SETTINGS_FILE, "r") as f:
                d = yaml.safe_load(f)
                self.specAnSettings = SpectrumAnalyzerSettings.parse_obj(d)
        except:
            self.specAnSettings = SpectrumAnalyzerSettings(attenuation = 2, enableInternalPreamp = True)
            self.saveSettingsSpecAn()
    
    def saveSettingsSpecAn(self):
        with open(self.COLDLLOAD_SPECAN_SETTINGS_FILE, "w") as f:
            yaml.dump(self.specAnSettings.dict(), f)
    
    def start(self, 
            bandLeftGHz: float = 9.95, 
            bandRightGHz: float = 10.05,
            ambSensorNum: int = 7):
        
        self.ambSensorNum = ambSensorNum
        self.power = -100.0
        self.wb = Workbook()
        self.ws = self.wb.active
        self.ws.append(['TS', 'Annotation', 'TAmbient', 'Power'])
        self.spectrumAnalyzer.configWideBand(bandLeftGHz, bandRightGHz, self.specAnSettings.sweepPoints)
        self.worker = threading.Thread(target = self.__measureLoop, daemon = True)
        self.worker.start()

    def stop(self):
        self.stopNow = True
        self.worker.join()
        self.stopped = not self.worker.is_alive()

    def pause(self, pause: bool):
        self.paused = pause

    def save(self, filename):
        self.wb.save(filename)

    def __measureLoop(self):
        while not self.stopNow:
            if not self.paused:
                time.sleep(0.5)
                self.power, success, msg = self.spectrumAnalyzer.measureWideBand()
                if not success:
                    print(msg)
                else:
                    try:
                        self.tAmb, tErr = self.temperatureMonitor.readSingle(self.ambSensorNum)
                    except:
                        self.tAmb = 0
                    ts = datetime.now()
                    print(f"{ts}: ambient:{self.tAmb} K, {self.power} dBm")
                    self.ws.append([ts, self.nextAnnotation, self.tAmb, self.power])
                    self.nextAnnotation = None
