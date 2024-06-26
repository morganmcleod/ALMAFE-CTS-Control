from INSTR.SpectrumAnalyzer.SpectrumAnalyzer import SpectrumAnalyzer, SpectrumAnalyzerSettings
from INSTR.TemperatureMonitor.Lakeshore218 import TemperatureMonitor
from INSTR.Chopper.Band6Chopper import Chopper
from Measure.NoiseTemperature.ColdLoadCalibration import ColdLoadCalibration
import logging
import keyboard

LOG_TO_FILE = True
LOG_FILE = 'ALMAFE-CTS-Control.log'

def main():
    specAn = SpectrumAnalyzer("TCPIP0::10.1.1.10::inst0::INSTR")
    tempMon = TemperatureMonitor("GPIB0::12::INSTR")
    chopper = Chopper()
    cal = ColdLoadCalibration(specAn, tempMon)
    cal.start()

    filename = "Coldload.xlsx"

    def help():
        print("\nA: Annotate next capture")
        print("C: Chopper cold")
        print("H: Chopper hot")
        print("S: Stop and save file")
        print("ESC: Quit")
        print("Any other key: show this help\n")
    help()

    done = False
    while not done:
        try:
            e = keyboard.read_event()
            if e.event_type == 'up':
                k = e.name 
                if k == 'esc':
                    done = True
                elif k == 'c':
                    chopper.gotoCold()
                    print("Moving chopper to cold load")
                elif k == 'h':
                    chopper.gotoHot()
                    print("Moving chopper to hot load")
                elif k == 's':
                    cal.stop()
                    filename = input("Filename: ")
                    cal.save(filename)
                    print(f"Saved to {filename}")
                    done = True
                elif k == 'a':
                    cal.pause(True)
                    cal.nextAnnotation = input("Annotation: ")
                    cal.pause(False)
                else:
                    help()
        except (KeyboardInterrupt, SystemExit):
            print('stopping.')
            done = True

if __name__ == "__main__":
    logger = logging.getLogger("ALMAFE-CTS-Control")
    logger.setLevel(logging.INFO)
    if LOG_TO_FILE:
        handler = logging.FileHandler(LOG_FILE)
    else:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt = '%(asctime)s %(levelname)s:%(message)s'))
    logger.addHandler(handler)

    logger.info("---- Cold load calibration start ----")
    main()
