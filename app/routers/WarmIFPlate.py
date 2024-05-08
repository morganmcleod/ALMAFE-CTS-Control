from fastapi import APIRouter
from hardware.WarmIFPlate import warmIFPlate
from CTSDevices.WarmIFPlate.InputSwitch import InputSelect
from schemas.common import SingleFloat, SingleInt, SingleBool
from schemas.DeviceInfo import DeviceInfo
from app.schemas.Response import MessageResponse
from DebugOptions import *

import logging
logger = logging.getLogger("ALMAFE-CTS-Control")

router = APIRouter(prefix="/warmif")

@router.get("/inputswitch/device_info", response_model = DeviceInfo)
async def get_DeviceInfo_InputSwitch():
    if SIMULATE:
        resource_name = "simulated input switch"
    else:
        resource_name = warmIFPlate.inputSwitch.switchController.inst.resource_name
    return DeviceInfo(
        resource_name = resource_name,
        is_connected = warmIFPlate.inputSwitch.isConnected())

@router.get("/yigfilter/device_info", response_model = DeviceInfo)
async def get_DeviceInfo_YIGFilter():
    if SIMULATE:
        resource_name = "simulated YIG filter"
    else:
        resource_name = warmIFPlate.yigFilter.switchController.inst.resource_name
    return DeviceInfo(
        resource_name = resource_name,        
        is_connected = warmIFPlate.yigFilter.isConnected()
    )

@router.get("/attenuation/device_info", response_model = DeviceInfo)
async def get_DeviceInfo_Attenuator():
    if SIMULATE:
        resource_name = "simulated attenuator"
    else:
        resource_name = warmIFPlate.attenuator.switchController.inst.resource_name
    return DeviceInfo(
        resource_name = resource_name,        
        is_connected = warmIFPlate.attenuator.isConnected()
    )

@router.get("/outputswitch/device_info", response_model = DeviceInfo)
async def get_DeviceInfo_OutputSwitch():
    if SIMULATE:
        resource_name = "simulated output switch"
    else:
        resource_name = warmIFPlate.outputSwitch.switchController.inst.resource_name
    return DeviceInfo(
        resource_name = resource_name,
        is_connected = warmIFPlate.outputSwitch.isConnected()
    )

@router.get("/noisesource/device_info", response_model = DeviceInfo)
async def get_DeviceInfo_NoiseSource():
    if SIMULATE:
        resource_name = "simulated noise source PSU"
    else:
        resource_name = warmIFPlate.noiseSource.powerSupply.inst.resource_name
    return DeviceInfo(
        resource_name = resource_name,
        is_connected = warmIFPlate.noiseSource.isConnected()
    )

@router.get("/inputswitch", response_model = MessageResponse)
async def getInputSwitch():
    position = warmIFPlate.inputSwitch.getValue()
    return MessageResponse(message = position.name, success = True)

@router.get("/yigfilter", response_model = SingleFloat)
async def getYigFilter():
    return SingleFloat(value = warmIFPlate.yigFilter.getFrequency())

@router.get("/attenuation", response_model = SingleInt)
async def getAtten():
    return SingleInt(value = warmIFPlate.attenuator.getValue())

@router.post('/inputswitch', response_model = MessageResponse)
async def setInputSwitch(value: int):
    if value == 0:
        sel = InputSelect.POL0_USB
    elif value == 1:
        sel = InputSelect.POL0_LSB
    elif value == 2:
        sel = InputSelect.POL1_USB
    elif value == 3:
        sel = InputSelect.POL1_LSB
    else:
        return MessageResponse(message = f"Invalid value for input switch: {value}", success = False)

    warmIFPlate.inputSwitch.setValue(sel)
    return MessageResponse(message = f"Set input switch to {sel}", success = True)

@router.post("/yigfilter", response_model = MessageResponse)
async def setYigFilter(value: float):
    if value < (warmIFPlate.yigFilter.MIN_TUNING_MHZ / 1000) or value > (warmIFPlate.yigFilter.MAX_TUNING_MHZ / 1000):
        return MessageResponse(message = f"Invalid frequency value for YIG filter: {value} GHz", success = False)
    warmIFPlate.yigFilter.setFrequency(value)
    return MessageResponse(message = f"Set YIG filter to {value} GHz", success = True)

@router.post("/attenuation", response_model = MessageResponse)
async def setAtten(value: int):
    if value < 0 or value > warmIFPlate.attenuator.MAX_ATTENUATION:
        return MessageResponse(message = f"Invalid value for attenuator: {value} dB", success = False)
    warmIFPlate.attenuator.setValue(value)
    return MessageResponse(message = f"Set IF attenuator to {value} dB", success = True)
