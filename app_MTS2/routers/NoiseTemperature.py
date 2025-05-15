from openpyxl import Workbook
from io import BytesIO
from datetime import datetime
from fastapi import APIRouter, Response
import app_MTS2.hardware.NoiseTemperature
coldLoad = app_MTS2.hardware.NoiseTemperature.coldLoad
import app_MTS2.hardware.IFSystem
ifSystem = app_MTS2.hardware.IFSystem.ifSystem
import app_MTS2.hardware.PowerDetect
powerDetect = app_MTS2.hardware.PowerDetect.powerDetect
import app_MTS2.measProcedure.NoiseTemperature 
settingsContainer = app_MTS2.measProcedure.NoiseTemperature.settingsContainer
import app_Common.measProcedure.DataDisplay
dataDisplay = app_Common.measProcedure.DataDisplay.dataDisplay
from Controllers.PowerDetect.Interface import DetectMode
from Measure.NoiseTemperature.schemas import *
from INSTR.ColdLoad.AMI1720 import FillMode
from INSTR.SpectrumAnalyzer.schemas import SpectrumAnalyzerSettings
from app_Common.schemas.common import SingleFloat
from app_Common.Response import ListResponse, MessageResponse, prepareListResponse

router = APIRouter(prefix="/noisetemp")

@router.get("/teststeps", response_model = TestSteps)
async def get_TestSteps():
    return settingsContainer.testSteps

@router.post("/teststeps",  response_model = MessageResponse)
async def put_TestSteps(steps: TestSteps):
    settingsContainer.testSteps = steps
    return MessageResponse(message = "Updated Test Steps " + settingsContainer.testSteps.getText(), success = True)

@router.post("/teststeps/reset",  response_model = MessageResponse)
async def reset_TestSteps():
    settingsContainer.setDefaultTestSteps()
    return MessageResponse(message = "Reset Test Steps " + settingsContainer.testSteps.getText(), success = True)

@router.get("/settings", response_model = CommonSettings)
async def get_TestSettings():
    return settingsContainer.commonSettings

@router.post("/settings",  response_model = MessageResponse)
async def put_Settings(settings: CommonSettings):
    settingsContainer.commonSettings = settings
    settingsContainer.saveSettingsCommon()
    return MessageResponse(message = "Updated Settings", success = True)

@router.post("/settings/reset",  response_model = MessageResponse)
async def reset_Settings():
    settingsContainer.setDefaultsCommon()
    return MessageResponse(message = "Reset common settings to defaults", success = True)

@router.get("/wifsettings", response_model = WarmIFSettings)
async def get_WifSettings():
    return settingsContainer.warmIFSettings

@router.post("/wifsettings",  response_model = MessageResponse)
async def put_NtSettings(settings: WarmIFSettings):
    settingsContainer.warmIFSettings = settings
    settingsContainer.saveSettingsWarmIF()
    return MessageResponse(message = "Updated Warm IF noise settings", success = True)

@router.post("/wifsettings/reset",  response_model = MessageResponse)
async def reset_wifsettings():
    settingsContainer.setDefaultsWarmIF()
    return MessageResponse(message = "Reset Warm IF Noise settings to defaults", success = True)

@router.get("/ntsettings", response_model = NoiseTempSettings)
async def get_NtSettings():
    return settingsContainer.noiseTempSettings

@router.post("/ntsettings",  response_model = MessageResponse)
async def put_NtSettings(settings: NoiseTempSettings):
    settingsContainer.noiseTempSettings = settings
    settingsContainer.saveSettingsNoiseTemp()
    return MessageResponse(message = "Updated Noise Temp settings", success = True)

@router.post("/ntsettings/reset",  response_model = MessageResponse)
async def reset_ntsettings():
    settingsContainer.setDefaultsNoiseTemp()
    return MessageResponse(message = "Reset Noise Temp settings to defaults", success = True)

@router.get("/lowgsettings", response_model = NoiseTempSettings)
async def get_NtSettings():
    return settingsContainer.loWgIntegritySettings

@router.post("/lowgsettings",  response_model = MessageResponse)
async def put_NtSettings(settings: NoiseTempSettings):
    settingsContainer.loWgIntegritySettings = settings
    settingsContainer.saveSettingsLOWGIntegrity()
    return MessageResponse(message = "Updated LO WG settings", success = True)

@router.post("/lowgsettings/reset",  response_model = MessageResponse)
async def reset_lowgsettings():
    settingsContainer.setDefaultsLOWGIntegrity()
    return MessageResponse(message = "Reset LO WG settings to defaults", success = True)

@router.get("/biasoptsettings", response_model = BiasOptSettings)
async def get_BiasOptSettings():
    return settingsContainer.biasOptSettings

@router.post("/biasoptsettings",  response_model = MessageResponse)
async def put_BiasOptSettings(settings: BiasOptSettings):
    settingsContainer.biasOptSettings = settings
    settingsContainer.saveSettingsBiasOpt()
    return MessageResponse(message = "Updated Bias Optimization settings", success = True)

@router.post("/biasoptsettings/reset",  response_model = MessageResponse)
async def reset_BiasOptSettings():
    settingsContainer.setDefaultsBiasOpt()
    return MessageResponse(message = "Reset Bias Optimization settings to defaults", success = True)

@router.get("/yfactorsettings", response_model = YFactorSettings)
async def get_YfactorSettings():
    return settingsContainer.yFactorSettings

@router.post("/yfactorsettings",  response_model = MessageResponse)
async def put_YfactorSettings(settings: YFactorSettings):
    settingsContainer.yFactorSettings = settings
    settingsContainer.saveSettingsYFactor()
    ifSystem.input_select = settings.inputSelect
    ifSystem.attenuation = settings.attenuation
    if powerDetect.detect_mode == DetectMode.METER or settings.detectMode == DetectMode.METER:
        ifSystem.frequency = settings.ifStart
        ifSystem.bandwidth = 0
    elif powerDetect.detect_mode == DetectMode.SPEC_AN or settings.detectMode == DetectMode.SPEC_AN:
        ifSystem.frequency = (settings.ifStop - settings.ifStart) / 2 + settings.ifStart
        ifSystem.bandwidth = settings.ifStop - settings.ifStart
    return MessageResponse(message = "Updated Y-factor settings", success = True)

@router.post("/yfactorsettings/reset",  response_model = MessageResponse)
async def reset_YfactorSettings():
    settingsContainer.setDefaultsYFactor()
    return MessageResponse(message = "Reset Y-factor settings to defaults", success = True)

@router.get("/yfactor/history", response_model = ListResponse)
async def get_YFactorHistory():
    return prepareListResponse(dataDisplay.yFactorPowers)

@router.get("/yfactor/excel", response_class = Response)
async def get_YFactorExcel(name: str):
    wb = Workbook()
    ws = wb.active
    ws.append(['inputName', 'pHot', 'pCold'])
    for item in dataDisplay.yFactorPowers:
        ws.append([item.inputName, item.pHot, item.pCold])
    buffer = BytesIO()
    wb.save(buffer)
    response = Response(buffer.getvalue(), media_type = "application/vnd.ms-excel")
    response.headers["Content-Disposition"] = f"attachment; filename={name}_{datetime.now().strftime('%Y-%m-%d_%H_%M_%S')}.xlsx"
    return response


@router.post("/yfactor/history/clear",  response_model = MessageResponse)
async def clear_YFactorHistory():
    dataDisplay.yFactorPowers = []
    return MessageResponse(message = "Cleared Y-factor history", success = True)

@router.get("/specan/settings_nt", response_model = SpectrumAnalyzerSettings)
async def get_SANTSettings():
    return settingsContainer.ntSpecAnSettings

@router.post("/specan/settings_nt",  response_model = MessageResponse)
async def put_SANTSettings(settings: SpectrumAnalyzerSettings):
    settingsContainer.ntSpecAnSettings = settings
    settingsContainer.saveSettingsNTSpecAn()
    return MessageResponse(message = "Updated spectrum analyzer settings for noise temperature", success = True)

@router.post("/specan/settings_nt/reset",  response_model = MessageResponse)
async def reset_ntSpecAnSettings():
    settingsContainer.setDefaultsNTSpecAn()
    return MessageResponse(message = "Reset spectrum analyzer settings for noise temperature to defaults", success = True)

@router.get("/specan/settings_ir", response_model = SpectrumAnalyzerSettings)
async def get_SANTSettings():
    return settingsContainer.irSpecAnSettings

@router.post("/specan/settings_ir",  response_model = MessageResponse)
async def put_SANTSettings(settings: SpectrumAnalyzerSettings):
    settingsContainer.irSpecAnSettings = settings
    settingsContainer.saveSettingsIRSpecAn()
    return MessageResponse(message = "Updated spectrum analyzer settings for image rejection", success = True)

@router.post("/specan/settings_ir/reset",  response_model = MessageResponse)
async def reset_irSpecAnSettings():
    settingsContainer.setDefaultsIRSpecAn()
    return MessageResponse(message = "Reset spectrum analyzer settings for image rejection to defaults", success = True)

@router.get("/coldload/level", response_model = SingleFloat)
async def get_ColdLoadLevel():
    level, err = coldLoad.checkLevel()
    return SingleFloat(value = level)

@router.post("/coldload/fillmode", response_model = MessageResponse)
async def put_ColdLoadFillMode(fillMode_: int):
    try:
        fillMode = FillMode(fillMode_)
        coldLoad.setFillMode(fillMode)
        return MessageResponse(message = f"Cold load: Set fill mode {fillMode}", success = True)
    except:
        return MessageResponse(message = "Cold load: Failed set fill mode", success = False)
        
@router.post("/coldload/startfill", response_model = MessageResponse)
async def put_ColdLoadStartFill():
    coldLoad.startFill()
    return MessageResponse(message = "Cold load: Fill started", success = True)

@router.post("/coldload/stopfill", response_model = MessageResponse)
async def put_ColdLoadStopFill():
    coldLoad.stopFill()
    return MessageResponse(message = "Cold load: Fill stopped", success = True)
