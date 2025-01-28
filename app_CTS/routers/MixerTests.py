from fastapi import APIRouter
from app_Common.Response import MessageResponse
import app_CTS.measProcedure.MixerTests
settingsContainer = app_CTS.measProcedure.MixerTests.settingsContainer
from AMB.schemas.MixerTests import IVCurveSettings, MagnetOptSettings, DefluxSettings
router = APIRouter(prefix="/mixertests")

@router.get("/settings/iv_curve", response_model = IVCurveSettings)
async def get_settings_iv_curve():
    return settingsContainer.ivCurveSettings

@router.put("/settings/iv_curve", response_model = MessageResponse)
async def put_settings_iv_curve(settings: IVCurveSettings):
    settingsContainer.ivCurveSettings = settings
    settingsContainer.saveSettingsIVCurve()
    return MessageResponse(message = "Updated I-V Curve settings", success = True)

@router.post("/settings/iv_curve/reset",  response_model = MessageResponse)
async def reset_settings_iv_curve():
    settingsContainer.setDefaultsIVCurve()
    return MessageResponse(message = "Reset I-V Curve settings to default", success = True)

@router.get("/settings/magnet_opt", response_model = MagnetOptSettings)
async def get_settings_magnet_opt():
    return settingsContainer.magnetOptSettings

@router.put("/settings/magnet_opt", response_model = MessageResponse)
async def put_settings_magnet_opt(settings: MagnetOptSettings):
    settingsContainer.magnetOptSettings = settings
    settingsContainer.saveSettingsMagOpt()
    return MessageResponse(message = "Updated Magnet Optimization settings", success = True)

@router.post("/settings/magnet_opt/reset",  response_model = MessageResponse)
async def reset_settings_magnet_opt():
    settingsContainer.setDefaultsMagOpt()
    return MessageResponse(message = "Reset Magnet Optimization settings to default", success = True)

@router.get("/settings/mixer_deflux", response_model = DefluxSettings)
async def get_settings_mixer_deflux():
    return settingsContainer.defluxSettings

@router.put("/settings/mixer_deflux", response_model = MessageResponse)
async def put_settings_mixer_deflux(settings: DefluxSettings):
    settingsContainer.defluxSettings = settings
    settingsContainer.saveSettingsDeflux()
    return MessageResponse(message = "Updated Mixer Deflux settings", success = True)

@router.post("/settings/mixer_deflux/reset",  response_model = MessageResponse)
async def reset_settings_mixer_deflux():
    settingsContainer.setDefaultsDeflux()
    return MessageResponse(message = "Reset Mixer Deflux settings to default", success = True)
