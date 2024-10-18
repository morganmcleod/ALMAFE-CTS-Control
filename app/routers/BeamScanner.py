import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Tuple, Optional
from schemas.common import SingleFloat
from Control.schemas.DeviceInfo import DeviceInfo
import measProcedure.BeamScanner
beamScanner = measProcedure.BeamScanner.beamScanner
motorController = measProcedure.BeamScanner.beamScanner.mc

import app.measProcedure.MeasurementStatus
measurementStatus = app.measProcedure.MeasurementStatus.measurementStatus()
from app.schemas.Response import MessageResponse
from .ConnectionManager import ConnectionManager
from INSTR.MotorControl.schemas import MotorStatus, MoveStatus, Position
from INSTR.PNA.schemas import MeasConfig, PowerConfig
from Measure.BeamScanner.schemas import MeasurementSpec, ScanList, ScanStatus, Rasters
from DebugOptions import *

logger = logging.getLogger("ALMAFE-CTS-Control")

router = APIRouter(prefix="/beamscan")
manager = ConnectionManager()

@router.websocket("/position_ws")
async def websocket_scandata_push(websocket: WebSocket):
    await manager.connect(websocket)
    lastPosition = None            
    try:
        while True:
            position = motorController.getPosition(cached = measurementStatus.getMeasuring())
            if position != lastPosition:
                lastPosition = position
                await manager.send(position.dict(), websocket)
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /position_ws")

@router.websocket("/motorstatus_ws")
async def websocket_scandata_push(websocket: WebSocket):
    await manager.connect(websocket)
    lastMotorStatus = None            
    try:
        while True:        
            motorStatus = motorController.getMotorStatus()
            if motorStatus != lastMotorStatus:
                lastMotorStatus = motorStatus
                await manager.send(motorStatus.dict(), websocket)
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /motorstatus_ws")

@router.websocket("/rasters_ws")
async def websocket_scandata_push(websocket: WebSocket):
    await manager.connect(websocket)
    lastKey = None
    lastIndex = 0
    try:
        while True:
            key, index = beamScanner.getLatestRasterInfo()
            if key > 0 and (index != lastIndex or key != lastKey):
                lastKey, lastIndex = key, index
                rasters = beamScanner.getRasters(latestOnly = True)
                if rasters and len(rasters.items):
                    await manager.send(rasters.items[0].dict(), websocket)
            await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /rasters_ws")
    except Exception as e:
        logger.exception(e)

@router.get("/rasters", response_model = Rasters)
async def get_Rasters(first: int, last: Optional[int] = -1):
    return beamScanner.getRasters(first, last)

@router.get("/mc/query", response_model = MessageResponse)
async def get_Query(query: str):
    """
    Low-level query to the motor controller.
    """
    try:
        response = motorController.query(bytes(query, 'ascii'), 3)
        if response:
            return MessageResponse(message = str(response), success = True)
        else:
            return MessageResponse(message = f"Error processing {query.getText()}", success = False)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)

@router.get("/mc/device_info", response_model = DeviceInfo)
async def get_mc_device_info():
    if SIMULATE:
        return DeviceInfo(
            name = 'Motor controller',
            resource = 'simulated',
            connected = True
        )
    else:
        return DeviceInfo(
            name = 'Motor controller',
            resource = f"{motorController.host}.{motorController.port}",
            connected = motorController.connected()
        )

@router.get("/mc/xy_speed", response_model = SingleFloat)
async def get_XYSpeed():
    return SingleFloat(value = motorController.getXYSpeed())

@router.put("/mc/xy_speed", response_model = MessageResponse)
async def put_XYSpeed(request: SingleFloat):
    motorController.setXYSpeed(request.value)
    return MessageResponse(message = "XY speed = " + request.getText() + " mm/sec", success = True)
    
@router.get("/mc/pol_speed", response_model = SingleFloat)
async def get_PolSpeed():
    return SingleFloat(value = motorController.getPolSpeed())

@router.put("/mc/pol_speed", response_model = MessageResponse)
async def put_PolSpeed(request: SingleFloat):
    motorController.setPolSpeed(request.value)
    return MessageResponse(message = "Pol speed = " + request.getText() + " deg/sec", success = True)

@router.put("/mc/xy_accel", response_model = MessageResponse)
async def put_XYAccel(request: SingleFloat):
    motorController.setXYAccel(request.value)
    return MessageResponse(message = "XY accel = " + request.getText() + " mm/sec^2", success = True)

@router.put("/mc/pol_accel", response_model = MessageResponse)
async def put_PolAccel(request: SingleFloat):
    motorController.setPolAccel(request.value)
    return MessageResponse(message = "Pol accel = " + request.getText() + " deg/sec^2", success = True)

@router.put("/mc/xy_decel", response_model = MessageResponse)
async def put_XYDecel(request: SingleFloat):
    motorController.setXYDecel(request.value)
    return MessageResponse(message = "XY decel = " + request.getText() + " mm/sec^2", success = True)

@router.put("/mc/pol_decel", response_model = MessageResponse)
async def put_PolDecel(request: SingleFloat):
    motorController.setPolDecel(request.value)
    return MessageResponse(message = "Pol decel = " + request.getText() + " deg/sec^2", success = True)

@router.get("/mc/pol_torque", response_model = SingleFloat)
async def get_PolTorque():
    return SingleFloat(value = motorController.getPolTorque())

@router.put("/mc/home/{axis}", response_model = MessageResponse)
async def put_HomeAxis(axis:str):
    try:
        motorController.homeAxis(axis)
        return MessageResponse(message = f"Homing axis '{axis}'", success = True)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)

@router.put("/mc/set_zero/{axis}", response_model = MessageResponse)
async def put_SetZeroAxis(axis:str):
    try:
        motorController.setZeroAxis(axis)
        return MessageResponse(message = f"Set zero for axis '{axis}'", success = True)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)

@router.put("/mc/servo_here", response_model = MessageResponse)
async def put_ServoHere():
    try:
        motorController.servoHere()
        return MessageResponse(message = "Servo Here done", success = True)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)

@router.put("/mc/setup", response_model = MessageResponse)
async def put_Setup():
    try:
        motorController.reset()
        return MessageResponse(message = "Setup done", success = True)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)

@router.get("/mc/get_errorcode", response_model = MessageResponse)
async def get_ErrorCode():
    try:
        msg = motorController.getErrorCode()
        return MessageResponse(message = msg, success = True)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)

@router.get("/mc/status", response_model = MotorStatus)
async def get_MotorStatus():
    return motorController.getMotorStatus()

@router.get("/mc/position", response_model = Position)
async def get_Position():
    return motorController.getPosition()

@router.put("/mc/next_pos", response_model = MessageResponse)
async def put_NextPos(pos:Position):
    try:
        motorController.setNextPos(pos)
        return MessageResponse(message = f"Set next pos = {pos.getText()}", success = True)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)

@router.get("/mc/estimate_move_time", response_model = SingleFloat)
async def get_estimateMoveTime():
    fromPos = motorController.getPosition()
    toPos = motorController.nextPos
    return SingleFloat(value = motorController.estimateMoveTime(fromPos, toPos))

@router.put("/mc/start_move", response_model = MessageResponse)
async def put_startMove(withTrigger:bool = False, timeout:float = None):
    try:
        motorController.startMove(withTrigger, timeout)
        return MessageResponse(message = "Motor controller start move", success = True)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)

@router.put("/mc/stop_move", response_model = MessageResponse)
async def put_StopMove():
    motorController.stopMove()
    return MessageResponse(message = "Motor controller stop move", success = True)

@router.get("/mc/move_status", response_model = MoveStatus)
async def get_MoveStatus():
    return motorController.getMoveStatus()

@router.get("/meas_spec", response_model = MeasurementSpec)
async def get_MeasurementSpec():
    return beamScanner.measurementSpec

@router.post("/meas_spec", response_model = MessageResponse)
async def put_MeasurementSpec(measurementSpec:MeasurementSpec):
    beamScanner.measurementSpec = measurementSpec
    beamScanner.saveSettings()
    return MessageResponse(message = "Updated measurement settings", success = True)

@router.post("/meas_spec/reset", response_model = MessageResponse)
async def reset_MeasurementSpec():
    beamScanner.defaultSetttings()
    return MessageResponse(message = "Reset measurement settings to default", success = True)

@router.get("/scan_list", response_model = ScanList)
async def get_ScanList(defaults: bool = False):
    return measProcedure.BeamScanner.defaultScanList if defaults else beamScanner.scanList

@router.put("/scan_list", response_model = MessageResponse)
async def put_ScanList(scanList: ScanList):
    beamScanner.scanList = scanList
    return MessageResponse(message = "Updated Scan List", success = True)

@router.get("/scan_status", response_model = ScanStatus)
async def get_ScanStatus():
    return beamScanner.scanStatus

@router.get("/pna/device_info", response_model = DeviceInfo)
async def get_PNAIsConnected():    
    if SIMULATE:
        return DeviceInfo(
            name = 'PNA',
            resource = 'simulated',
            connected = True
        )
    else:
        return DeviceInfo(
            name = 'PNA',
            resource = beamScanner.pna.inst.resource,
            connected = beamScanner.pna.connected()
    )

@router.get("/pna/idquery", response_model = MessageResponse)
async def get_PNAIdQuery():
    ret = beamScanner.pna.idQuery()
    return MessageResponse(message = ret if ret else "None", success = True if ret else False)

@router.post("/pna/reset", response_model = MessageResponse)
async def post_PNAReset():
    beamScanner.pna.reset()
    return MessageResponse(message = "PNA reset", success = True)

@router.get("/pna/measconfig", response_model = MeasConfig)
async def get_PNAMeasConfig():
    return beamScanner.pna.measConfig

@router.post("/pna/measconfig", response_model = MessageResponse)
async def post_PNAMeasConfig(config:MeasConfig):
    beamScanner.pna.setMeasConfig(config)
    return MessageResponse(message = "PNA set MeasConfig: " + config.getText(), success = True)

@router.get("/pna/powerconfig", response_model = PowerConfig)
async def get_PNAPowerConfig():
    return beamScanner.pna.powerConfig

@router.post("/pna/powerconfig", response_model = MessageResponse)
async def post_PNAMeasConfig(config:PowerConfig):
    beamScanner.pna.setPowerConfig(config)
    return MessageResponse(message = "PNA set PowerConfig" + config.getText(), success = True)

@router.get("/pna/trace", response_model = Tuple[List[float], List[float]])
async def get_PNATrace():
    return beamScanner.pna.getTrace()

@router.get("/pna/ampphase", response_model = Tuple[float])
async def get_PNAAmpPhase():
    return beamScanner.pna.getAmpPhase()
