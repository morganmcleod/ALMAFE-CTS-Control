# ALMAFE-CTS-Control
## Measurement software for the ALMA band 6 cartridge test systems (CTS)
This application implements the back end for operating all of the CTS hardware and measurements.
It uses [FastAPI](https://fastapi.tiangolo.com/) to expose an HTTP/REST interface.
It is designed to be operated from a front end user application which communicates with the interface.

## Project structure
### Top level directory
**This should be the current working directory whenever the app is running, so that it can access the files here.**

**This directory should be on the PYTHONPATH**

Contents:
 * ALMAFE-CTS-Control_template.ini
    
    ALMFE-CTS-Control.ini **No check into Git**

    Settings to customize the installed CTS hardware, database connection
 * FrontEndAMBDLL.ini

    Settings for initializing CAN bus connections using AMBConnectionDLL
 * DebugOptions.py

    Set global debugging options. All are normally False for measurement.

 * ALMAFE-CTS-Control.log

    Activity and debugging log for the application **No check in to Git**
 * Classes.mdzip

    A class diagram for use with MagicDraw
 * requirements.txt

    Python packages this application depends upon.

    `pip install -r requirements.txt`
  * .gitignore

    Specifies files and patterns which should not be checked into Git

#### app/
 * main.py

    The application's main module
#### app/database
 * CTSDB.py
 
    For configuring and establishing the database connection to **dbBand6Cart**
#### app/hardware
Modules to create the objects that control the hardware. The objects' behavior is defined by the modules imported here.
 * BeamScanner.py

    motorController and pna
 * FEMC.py

    ccaDevice, loDevice, rfSrcDevice, femcDevice
 * IFSystem.py

    ifSystem is implemented either in terms of warmIFPlate or externalSwitch
 * NoiseTemperature.py

    chopper, coldLoad, powerSupply (for noise source diode), temperatureMonitor
 * PowerDetect.py

    powerDetect is implement either in terms of powerMeter or spectrumAnalyzer
 * ReferenceSources.py

    loReference, rfReference
 * Stability.py

    voltMeter used for Amplitude Stability
#### app/measProcedure
Modules to create the objects that sequence the measurements. The objects' behavior is defined by the modules imported here.  These are composed from the objects in app/hardware.
 * BeamScanner.py

    beamScanner, defaultScanList
 * DataDisplay.py

    holds all the results for display to the users
 * MeasurementStatus.py

    holds info about the current measurement
 * MixerTests.py

    settingsContainer for I-V curves, magnet optimization, mixer deflux
 * NoiseTemperature.py
    
    settingsContainer for noise temperature tests    
 * ScriptRunner.py
    
    handles starting and stopping measurements, running custom scripts
 * Stability.py

    amplitudeStablilty, phaseStability and some objects they depend on
#### app/routers
These implement the HTTP/REST interface which is exposed by FastAPI.
#### app/schemas
Data structures which define how messages are passed over the HTTP/REST interface.  Based on [Pydantic](https://docs.pydantic.dev/latest/)
#### app/scripts
Several (but not yet all) measurements are controlled by top-level scripts.  This allows future customization of how data is taken and how it is stored and displayed.  (As opposed to baking one fixed way into a measurement procedure class.)
#### Control/
Mid-level interfaces and hardware components.  These allow procedures in Measure/ to be implemented in terms of interfaces rather than concrete devices.
 * CartAssembly.py

    Coordinates CCADevice and LODevice including tuning and biasing; loads operating parameters from **dbBand6Cart**
 * RFSource.py

    Operates an LODevice as an RF source including tuning and biasing; loads operating parameters from **dbBand6Cart**
 * IFAutoLevel.py

    Coordinates PowerDetect and IFSystem to implement auto setting of IF level.
 * RFAutoLevel.py

    Coordinates PowerDetect, IFSystem, and RFSource to implement auto-setting of RF transmit level.
 * PBAController.py

    Implements a probablisic binary search.
#### Control/IFSystem
Represents the IF system which is outside of the device under test.
 * Interface.py is the call inteface from procedures in Measure/
 * TemporaryB6V2.py is the CTS-2 switches and spectrum analyzer.
 * WarmIFPlate.py is the CTS-1 warm IF plate.
#### Control/PowerDetect
Represents IF power detection devices in the CTS.
 * Interface.py is the call inteface from procedures in Measure/
 * PDPNA.py is the PNA, used by beam scanner, phase stability
 * PDPowerMeter is the CTS-1 power meter
 * PDSpecAn is the CTS-2 spectrum analzyer
 * PDVoltMeter is the DVM used for amplitude stability
 * IFPowerImpl implents an interface defined in ALMAFE-AmbDeviceLibrary to allow I-V-Power curves.
#### Control/schemas
 * DeviceInfo is a shared data structure for various devices to report their status.
#### Measure/
Define the measurement procedures or steps which may be scripted to accomplish a measurement.
 * BeamScanner
 * MixerTests: I-V curves, magnet optimization, mixer deflux
 * NoiseTemperature
 * Stability: amplitude and phase
#### Measure/Shared
 * DataDisplay.py: define the object which holds data for display to the user
 * makeSteps.py: utility for making lists of LO, IF steps
 * MeasurementStatus: define the object which holds status of the current measurement
 * ScriptRunner: define the object which starts and stops measurements procedures and scripts
 * SelectPolarization: enum to define POL0, POL1, or BOTH
#### Settings/
YAML files which contain settings for how measuremetns or devices are operated
#### Tests/
Various test applications
