from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Tuple
from schemas.common import SingleBool, SingleFloat
import hardware.BeamScanner as BeamScanner
from Response import KeyResponse, MessageResponse
import asyncio
from .ConnectionManager import ConnectionManager
from .Database import CTSDB
from DBBand6Cart.CartTests import CartTest, CartTests
from DBBand6Cart.TestTypes import TestTypeIds
from CTSDevices.MotorControl.schemas import MotorStatus, MoveStatus, Position
from CTSDevices.PNA.schemas import MeasConfig, PowerConfig
from Measure.BeamScanner.schemas import MeasurementSpec, ScanList, ScanStatus, SubScansOption
from socket import getfqdn

import logging
logger = logging.getLogger("ALMAFE-CTS-Control")

router = APIRouter(prefix="/beamscan")
manager = ConnectionManager()

@router.websocket("/position_ws")
async def websocket_scandata_request(websocket: WebSocket):
    global logger
    await manager.connect(websocket)
    lastPosition = None            
    try:
        while True:        
            position = BeamScanner.motorController.getPosition()
            if position != lastPosition:
                lastPosition = position
                await manager.send(position.dict(), websocket)
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /position_ws")

@router.websocket("/rasters_ws")
async def websocket_scandata_push(websocket: WebSocket):
    global logger
    await manager.connect(websocket)
    try:
        while True:
            rasters = BeamScanner.beamScanner.getRasters()
            if rasters:
                await manager.send(rasters.dict(), websocket)
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /rasters_ws")
    except Exception as e:
        logger.exception(e)

@router.get("/mc/query", response_model = MessageResponse)
async def get_Query(query: str):
    """
    Low-level query to the motor controller.
    """
    try:
        response = BeamScanner.motorController.query(bytes(query, 'ascii'), 3)
        if response:
            return MessageResponse(message = str(response), success = True)
        else:
            return MessageResponse(message = f"Error processing {query.getText()}", success = False)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)

@router.get("/mc/isconnected", response_model = SingleBool)
async def get_IsConnected():
    return SingleBool(value = BeamScanner.motorController.isConnected())

@router.get("/mc/xy_speed", response_model = SingleFloat)
async def get_XYSpeed():
    return SingleFloat(value = BeamScanner.motorController.getXYSpeed())

@router.put("/mc/xy_speed", response_model = MessageResponse)
async def put_XYSpeed(request: SingleFloat):
    BeamScanner.motorController.setXYSpeed(request.value)
    return MessageResponse(message = "XY speed = " + request.getText() + " mm/sec", success = True)
    
@router.get("/mc/pol_speed", response_model = SingleFloat)
async def get_PolSpeed():
    return SingleFloat(value = BeamScanner.motorController.getPolSpeed())

@router.put("/mc/pol_speed", response_model = MessageResponse)
async def put_PolSpeed(request: SingleFloat):
    BeamScanner.motorController.setPolSpeed(request.value)
    return MessageResponse(message = "Pol speed = " + request.getText() + " deg/sec", success = True)

@router.put("/mc/xy_accel", response_model = MessageResponse)
async def put_XYAccel(request: SingleFloat):
    BeamScanner.motorController.setXYAccel(request.value)
    return MessageResponse(message = "XY accel = " + request.getText() + " mm/sec^2", success = True)

@router.put("/mc/pol_accel", response_model = MessageResponse)
async def put_PolAccel(request: SingleFloat):
    BeamScanner.motorController.setPolAccel(request.value)
    return MessageResponse(message = "Pol accel = " + request.getText() + " deg/sec^2", success = True)

@router.put("/mc/xy_decel", response_model = MessageResponse)
async def put_XYDecel(request: SingleFloat):
    BeamScanner.motorController.setXYDecel(request.value)
    return MessageResponse(message = "XY decel = " + request.getText() + " mm/sec^2", success = True)

@router.put("/mc/pol_decel", response_model = MessageResponse)
async def put_PolDecel(request: SingleFloat):
    BeamScanner.motorController.setPolDecel(request.value)
    return MessageResponse(message = "Pol decel = " + request.getText() + " deg/sec^2", success = True)

@router.get("/mc/pol_torque", response_model = SingleFloat)
async def get_PolTorque():
    return SingleFloat(value = BeamScanner.motorController.getPolTorque())

@router.put("/mc/home/{axis}", response_model = MessageResponse)
async def put_HomeAxis(axis:str):
    try:
        BeamScanner.motorController.homeAxis(axis)
        return MessageResponse(message = f"Homing axis '{axis}'", success = True)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)

@router.put("/mc/set_zero/{axis}", response_model = MessageResponse)
async def put_SetZeroAxis(axis:str):
    try:
        BeamScanner.motorController.setZeroAxis(axis)
        return MessageResponse(message = f"Set zero for axis '{axis}'", success = True)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)

@router.put("/mc/servo_here", response_model = MessageResponse)
async def put_ServoHere():
    try:
        BeamScanner.motorController.setZeroAxis(axis)
        return MessageResponse(message = f"Set zero for axis '{axis}'", success = True)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)


@router.get("/mc/status", response_model = MotorStatus)
async def get_MotorStatus():
    return BeamScanner.motorController.getMotorStatus()

@router.get("/mc/position", response_model = Position)
async def get_Position():
    return BeamScanner.motorController.getPosition()

@router.put("/mc/next_pos", response_model = MessageResponse)
async def put_NextPos(pos:Position):
    try:
        BeamScanner.motorController.setNextPos(pos)
        return MessageResponse(message = f"Set next pos = {pos.getText()}", success = True)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)

@router.get("/mc/estimate_move_time", response_model = SingleFloat)
async def get_estimateMoveTime():
    fromPos = BeamScanner.motorController.getPosition()
    toPos = BeamScanner.motorController.nextPos
    return SingleFloat(value = BeamScanner.motorController.estimateMoveTime(fromPos, toPos))

@router.put("/mc/start_move", response_model = MessageResponse)
async def put_startMove(withTrigger:bool = False, timeout:float = None):
    try:
        BeamScanner.motorController.startMove(withTrigger, timeout)
        return MessageResponse(message = "Motor controller start move", success = True)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)

@router.put("/mc/stop_move", response_model = MessageResponse)
async def put_StopMove():
    BeamScanner.motorController.stopMove()
    return MessageResponse(message = "Motor controller stop move", success = True)

@router.get("/mc/move_status", response_model = MoveStatus)
async def get_MoveStatus():
    return BeamScanner.motorController.getMoveStatus()

@router.put("/start", response_model = KeyResponse)
async def put_Start(cartTest:CartTest):
    cartTestsDb = CartTests(driver = CTSDB())
    cartTest.fkTestType = TestTypeIds.BEAM_PATTERN.value
    cartTest.testSysName = getfqdn()
    BeamScanner.beamScanner.keyCartTest = cartTestsDb.create(cartTest)
    if (BeamScanner.beamScanner.keyCartTest):
        BeamScanner.beamScanner.start()
        return KeyResponse(key = BeamScanner.beamScanner.keyCartTest, message = "Beam scans started", success = True)
    else:
        return KeyResponse(key = 0, message = "Failed creating CartTest record", success = False)

@router.put("/stop", response_model = MessageResponse)
async def put_Stop():
    BeamScanner.beamScanner.stop()
    return MessageResponse(message = "Beam scans stopped", success = True)

@router.get("/meas_spec", response_model = MeasurementSpec)
async def get_MeasurementSpec():
    return BeamScanner.beamScanner.measurementSpec

@router.post("/meas_spec", response_model = MessageResponse)
async def put_MeasurementSpec(measurementSpec:MeasurementSpec):
    BeamScanner.beamScanner.measurementSpec = measurementSpec
    return MessageResponse(message = "Updated MeasurementSpec", success = True)

@router.get("/scan_list", response_model = ScanList)
async def get_ScanList():
    return BeamScanner.beamScanner.scanList

@router.post("/scan_list/enable/all", response_model = MessageResponse)
async def put_ScanListItemEnableAll(enable: bool):
    for item in BeamScanner.beamScanner.scanList.items:
        item.enable = enable
    return MessageResponse(message = f"Updated ScanList all={enable}", success = True)

@router.post("/scan_list/enable/{index}", response_model = MessageResponse)
async def put_ScanListItemEnable(index: int, enable: bool):
    try:
        BeamScanner.beamScanner.scanList.items[index].enable = enable
        return MessageResponse(message = f"Updated ScanList item {index}={enable}", success = True)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)

@router.post("/scan_list/subscans/all", response_model = MessageResponse)
async def put_ScanListItemEnableAll(what: dict):
    try:
        subScan = list(what.keys())[0]
        enable = list(what.values())[0]
        if subScan in SubScansOption.__fields__.keys():
            for item in BeamScanner.beamScanner.scanList.items:
                setattr(item.subScansOption, subScan, enable)
            return MessageResponse(message = f"Updated ScanList all={subScan}:{enable}", success = True)
        else:
            return MessageResponse(message = f"invalid input:{what}", success = False)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)


@router.post("/scan_list/subscans/{index}", response_model = MessageResponse)
async def put_ScanListSubScansOption(index: int, subScansOption: SubScansOption):
    try:
        BeamScanner.beamScanner.scanList.items[index].subScansOption = subScansOption
        return MessageResponse(message = f"Updated ScanList item {index}:{subScansOption.getText()}", success = True)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)

@router.get("/scan_status", response_model = ScanStatus)
async def get_ScanStatus():
    return BeamScanner.beamScanner.scanStatus

@router.get("/pna/idquery", response_model = MessageResponse)
async def get_PNAIdQuery():
    ret = BeamScanner.pna.idQuery()
    return MessageResponse(message = ret if ret else "None", success = True if ret else False)

@router.post("/pna/reset", response_model = MessageResponse)
async def post_PNAReset():
    BeamScanner.pna.reset()
    return MessageResponse(message = "PNA reset", success = True)

@router.get("/pna/measconfig", response_model = MeasConfig)
async def get_PNAMeasConfig():
    return BeamScanner.pna.measConfig

@router.post("/pna/measconfig", response_model = MessageResponse)
async def post_PNAMeasConfig(config:MeasConfig):
    BeamScanner.pna.setMeasConfig(config)
    return MessageResponse(message = "PNA set MeasConfig: " + config.getText(), success = True)

@router.get("/pna/powerconfig", response_model = PowerConfig)
async def get_PNAPowerConfig():
    return BeamScanner.pna.powerConfig

@router.post("/pna/powerconfig", response_model = MessageResponse)
async def post_PNAMeasConfig(config:PowerConfig):
    BeamScanner.pna.setPowerConfig(config)
    return MessageResponse(message = "PNA set PowerConfig" + config.getText(), success = True)

@router.get("/pna/trace", response_model = Tuple[List[float], List[float]])
async def get_PNATrace():
    return BeamScanner.pna.getTrace()

@router.get("/pna/ampphase", response_model = Tuple[float])
async def get_PNAAmpPhase():
    return BeamScanner.pna.getAmpPhase()
