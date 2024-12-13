from openpyxl import Workbook
from io import BytesIO
from datetime import datetime
from fastapi import APIRouter, Response
import hardware.NoiseTemperature
coldLoad = hardware.NoiseTemperature.coldLoad
import hardware.IFSystem
ifSystem = hardware.IFSystem.ifSystem
import hardware.PowerDetect
powerDetect = hardware.PowerDetect.powerDetect
import measProcedure.NoiseTemperature 
nt_settings = measProcedure.NoiseTemperature.settingsContainer
import app.measProcedure.DataDisplay
dataDisplay = app.measProcedure.DataDisplay.dataDisplay
from Control.PowerDetect.Interface import DetectMode
from Measure.NoiseTemperature.schemas import TestSteps, CommonSettings, WarmIFSettings, NoiseTempSettings, YFactorSettings
from INSTR.ColdLoad.AMI1720 import FillMode
from INSTR.SpectrumAnalyzer.schemas import SpectrumAnalyzerSettings
from schemas.common import SingleFloat
from app.schemas.Response import ListResponse, MessageResponse, prepareListResponse

router = APIRouter(prefix="/noisetemp")

@router.get("/teststeps", response_model = TestSteps)
async def get_TestSteps():
    return nt_settings.testSteps

@router.post("/teststeps",  response_model = MessageResponse)
async def put_TestSteps(steps: TestSteps):
    nt_settings.testSteps = steps
    return MessageResponse(message = "Updated Test Steps " + nt_settings.testSteps.getText(), success = True)

@router.post("/teststeps/reset",  response_model = MessageResponse)
async def reset_TestSteps():
    nt_settings.setDefaultTestSteps()
    return MessageResponse(message = "Reset Test Steps " + nt_settings.testSteps.getText(), success = True)

@router.get("/settings", response_model = CommonSettings)
async def get_TestSettings():
    return nt_settings.commonSettings

@router.post("/settings",  response_model = MessageResponse)
async def put_Settings(settings: CommonSettings):
    nt_settings.commonSettings = settings
    nt_settings.saveSettingsCommon()
    return MessageResponse(message = "Updated Settings", success = True)

@router.post("/settings/reset",  response_model = MessageResponse)
async def reset_Settings():
    nt_settings.setDefaultsCommon()
    return MessageResponse(message = "Reset common settings to defaults", success = True)

@router.get("/wifsettings", response_model = WarmIFSettings)
async def get_WifSettings():
    return nt_settings.warmIFSettings

@router.post("/wifsettings",  response_model = MessageResponse)
async def put_NtSettings(settings: WarmIFSettings):
    nt_settings.warmIFSettings = settings
    nt_settings.saveSettingsWarmIF()
    return MessageResponse(message = "Updated Warm IF noise settings", success = True)

@router.post("/wifsettings/reset",  response_model = MessageResponse)
async def reset_wifsettings():
    nt_settings.setDefaultsWarmIF()
    return MessageResponse(message = "Reset Warm IF Noise settings to defaults", success = True)

@router.get("/ntsettings", response_model = NoiseTempSettings)
async def get_NtSettings():
    return nt_settings.noiseTempSettings

@router.post("/ntsettings",  response_model = MessageResponse)
async def put_NtSettings(settings: NoiseTempSettings):
    nt_settings.noiseTempSettings = settings
    nt_settings.saveSettingsNoiseTemp()
    return MessageResponse(message = "Updated Noise Temp settings", success = True)

@router.post("/ntsettings/reset",  response_model = MessageResponse)
async def reset_ntsettings():
    nt_settings.setDefaultsNoiseTemp()
    return MessageResponse(message = "Reset Noise Temp settings to defaults", success = True)

@router.get("/lowgsettings", response_model = NoiseTempSettings)
async def get_NtSettings():
    return nt_settings.loWgIntegritySettings

@router.post("/lowgsettings",  response_model = MessageResponse)
async def put_NtSettings(settings: NoiseTempSettings):
    nt_settings.loWgIntegritySettings = settings
    nt_settings.saveSettingsLOWGIntegrity()
    return MessageResponse(message = "Updated LO WG settings", success = True)

@router.post("/lowgsettings/reset",  response_model = MessageResponse)
async def reset_lowgsettings():
    nt_settings.setDefaultsLOWGIntegrity()
    return MessageResponse(message = "Reset LO WG settings to defaults", success = True)

@router.get("/yfactorsettings", response_model = YFactorSettings)
async def get_YfactorSettings():
    return nt_settings.yFactorSettings

@router.post("/yfactorsettings",  response_model = MessageResponse)
async def put_YfactorSettings(settings: YFactorSettings):
    nt_settings.yFactorSettings = settings
    nt_settings.saveSettingsYFactor()
    ifSystem.input_select = settings.inputSelect
    ifSystem.attenuation = settings.attenuation
    if powerDetect.detect_mode == DetectMode.METER or settings.detectMode == DetectMode.METER:
        ifSystem.frequency = settings.ifStart
        ifSystem.bandwidth = 0
    elif powerDetect.detect_mode == DetectMode.SPEC_AN or settings.detectMode == DetectMode.SPEC_AN:
        ifSystem.frequency = (settings.ifStop - settings.ifStart) / 2
        ifSystem.bandwidth = settings.ifStop - settings.ifStart
    return MessageResponse(message = "Updated Y-factor settings", success = True)

@router.post("/yfactorsettings/reset",  response_model = MessageResponse)
async def reset_YfactorSettings():
    nt_settings.setDefaultsYFactor()
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
    return nt_settings.ntSpecAnSettings

@router.post("/specan/settings_nt",  response_model = MessageResponse)
async def put_SANTSettings(settings: SpectrumAnalyzerSettings):
    nt_settings.ntSpecAnSettings = settings
    nt_settings.saveSettingsNTSpecAn()
    return MessageResponse(message = "Updated spectrum analyzer settings for noise temperature", success = True)

@router.post("/specan/settings_nt/reset",  response_model = MessageResponse)
async def reset_ntSpecAnSettings():
    nt_settings.setDefaultsNTSpecAn()
    return MessageResponse(message = "Reset spectrum analyzer settings for noise temperature to defaults", success = True)

@router.get("/specan/settings_ir", response_model = SpectrumAnalyzerSettings)
async def get_SANTSettings():
    return nt_settings.irSpecAnSettings

@router.post("/specan/settings_ir",  response_model = MessageResponse)
async def put_SANTSettings(settings: SpectrumAnalyzerSettings):
    nt_settings.irSpecAnSettings = settings
    nt_settings.saveSettingsIRSpecAn()
    return MessageResponse(message = "Updated spectrum analyzer settings for image rejection", success = True)

@router.post("/specan/settings_ir/reset",  response_model = MessageResponse)
async def reset_irSpecAnSettings():
    nt_settings.setDefaultsIRSpecAn()
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
