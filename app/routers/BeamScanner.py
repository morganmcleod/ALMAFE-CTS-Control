from fastapi import APIRouter
from typing import Optional
from schemas.BeamScanner import *
from schemas.common import SingleBool, SingleFloat
import hardware.BeamScanner as BeamScanner
from Response import MessageResponse

router = APIRouter(prefix="/beamscan")

@router.get("/mc/query", tags=["BeamScan"], response_model = MessageResponse)
async def get_Query(query: ControllerQuery):
    """
    Low-level query to the motor controller.
    """
    try:
        response = BeamScanner.motorController.query(bytes(query.request), query.replySize)
        if response:
            return MessageResponse(message = str(response), success = True)
        else:
            return MessageResponse(message = f"Error processing {query.getText()}", success = False)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)

@router.get("/mc/isconnected", tags=["BeamScan"], response_model = SingleBool)
async def get_IsConnected():
    return SingleBool(value = BeamScanner.motorController.isConnected())

@router.get("/mc/xy_speed", tags=["BeamScan"], response_model = SingleFloat)
async def get_XYSpeed():
    return SingleFloat(value = BeamScanner.motorController.getXYSpeed())

@router.put("/mc/xy_speed", tags=["BeamScan"], response_model = MessageResponse)
async def put_XYSpeed(request: SingleFloat):
    BeamScanner.motorController.setXYSpeed(request.value)
    return MessageResponse(message = "XY speed = " + request.getText() + " mm/sec", success = True)
    
@router.get("/mc/pol_speed", tags=["BeamScan"], response_model = SingleFloat)
async def get_PolSpeed():
    return SingleFloat(value = BeamScanner.motorController.getPolSpeed())

@router.put("/mc/pol_speed", tags=["BeamScan"], response_model = MessageResponse)
async def put_PolSpeed(request: SingleFloat):
    BeamScanner.motorController.setPolSpeed(request.value)
    return MessageResponse(message = "Pol speed = " + request.getText() + " deg/sec", success = True)

@router.put("/mc/xy_accel", tags=["BeamScan"], response_model = MessageResponse)
async def put_XYAccel(request: SingleFloat):
    BeamScanner.motorController.setXYAccel(request.value)
    return MessageResponse(message = "XY accel = " + request.getText() + " mm/sec^2", success = True)

@router.put("/mc/pol_accel", tags=["BeamScan"], response_model = MessageResponse)
async def put_PolAccel(request: SingleFloat):
    BeamScanner.motorController.setPolAccel(request.value)
    return MessageResponse(message = "Pol accel = " + request.getText() + " deg/sec^2", success = True)

@router.put("/mc/xy_decel", tags=["BeamScan"], response_model = MessageResponse)
async def put_XYDecel(request: SingleFloat):
    BeamScanner.motorController.setXYDecel(request.value)
    return MessageResponse(message = "XY decel = " + request.getText() + " mm/sec^2", success = True)

@router.put("/mc/pol_decel", tags=["BeamScan"], response_model = MessageResponse)
async def put_PolDecel(request: SingleFloat):
    BeamScanner.motorController.setPolDecel(request.value)
    return MessageResponse(message = "Pol decel = " + request.getText() + " deg/sec^2", success = True)

@router.get("/mc/pol_torque", tags=["BeamScan"], response_model = SingleFloat)
async def get_PolTorque():
    return SingleFloat(value = BeamScanner.motorController.getPolTorque())

@router.put("/mc/home/{axis}", tags=["BeamScan"], response_model = MessageResponse)
async def put_HomeAxis(axis:str):
    try:
        BeamScanner.motorController.homeAxis(axis)
        return MessageResponse(message = f"Homing axis '{axis}'", success = True)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)

@router.put("/mc/set_zero/{axis}", tags=["BeamScan"], response_model = MessageResponse)
async def put_SetZeroAxis(axis:str):
    try:
        BeamScanner.motorController.setZeroAxis(axis)
        return MessageResponse(message = f"Set zero for axis '{axis}'", success = True)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)

@router.put("/mc/trigger_interval", tags=["BeamScan"], response_model = MessageResponse)
async def put_TriggerInterval(request: SingleFloat):
    BeamScanner.motorController.setTriggerInterval(request.value)
    return MessageResponse(message = f"Trigger interval = {request.value} mm", success = True)

@router.get("/mc/status", tags=["BeamScan"], response_model = MotorStatus)
async def get_MotorStatus():
    return BeamScanner.motorController.getMotorStatus()

@router.get("/mc/position", tags=["BeamScan"], response_model = Position)
async def get_Position():
    return BeamScanner.motorController.getPosition()

@router.put("/mc/next_pos", tags=["BeamScan"], response_model = MessageResponse)
async def put_NextPos(pos:Position):
    try:
        BeamScanner.motorController.setNextPos(pos)
        return MessageResponse(message = f"Set next pos = {pos.getText()}", success = True)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)

@router.get("/mc/estimate_move_time", tags=["BeamScan"], response_model = SingleFloat)
async def get_estimateMoveTime():
    fromPos = BeamScanner.motorController.getPosition()
    toPos = BeamScanner.motorController.nextPos
    return SingleFloat(value = BeamScanner.motorController.estimateMoveTime(fromPos, toPos))

@router.put("/mc/start_move", tags=["BeamScan"], response_model = MessageResponse)
async def put_startMove(trigger: bool = False):
    try:
        BeamScanner.motorController.startMove(trigger)
        return MessageResponse(message = "Start move", success = True)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)

@router.put("/mc/stop_move", tags=["BeamScan"], response_model = MessageResponse)
async def put_StopMove():
    BeamScanner.motorController.stopMove()
    return MessageResponse(message = "Stop move", success = True)

@router.get("/mc/move_status", tags=["BeamScan"], response_model = MoveStatus)
async def get_MoveStatus():
    return BeamScanner.motorController.getMoveStatus()

@router.put("/start", tags=["BeamScan"], response_model = MessageResponse)
async def put_Start():
    BeamScanner.beamScanner.start()
    return MessageResponse(message = "Scanner started", success = True)

@router.put("/stop", tags=["BeamScan"], response_model = MessageResponse)
async def put_Stop():
    BeamScanner.beamScanner.stop()
    return MessageResponse(message = "Scanner stopped", success = True)

@router.get("/meas_spec", tags=["BeamScan"], response_model = MeasurementSpec)
async def get_MeasurementSpec():
    return BeamScanner.beamScanner.measurementSpec

@router.post("/meas_spec", tags=["BeamScan"], response_model = MessageResponse)
async def put_MeasurementSpec(measurementSpec:MeasurementSpec):
    BeamScanner.beamScanner.measurementSpec = measurementSpec
    return MessageResponse(message = "Updated MeasurementSpec", success = True)

@router.get("/scan_list", tags=["BeamScan"], response_model = ScanList)
async def get_ScanList():
    return BeamScanner.beamScanner.scanList

@router.post("/scan_list/enable/all", tags=["BeamScan"], response_model = MessageResponse)
async def put_ScanListItemEnableAll(enable: bool):
    for item in BeamScanner.beamScanner.scanList.items:
        item.enable = enable
    return MessageResponse(message = f"Updated ScanList all={enable}", success = True)

@router.post("/scan_list/enable/{index}", tags=["BeamScan"], response_model = MessageResponse)
async def put_ScanListItemEnable(index: int, enable: bool):
    try:
        BeamScanner.beamScanner.scanList.items[index].enable = enable
        return MessageResponse(message = f"Updated ScanList item {index}={enable}", success = True)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)

@router.post("/scan_list/subscans/all", tags=["BeamScan"], response_model = MessageResponse)
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


@router.post("/scan_list/subscans/{index}", tags=["BeamScan"], response_model = MessageResponse)
async def put_ScanListSubScansOption(index: int, subScansOption: SubScansOption):
    try:
        BeamScanner.beamScanner.scanList.items[index].subScansOption = subScansOption
        return MessageResponse(message = f"Updated ScanList item {index}:{subScansOption.getText()}", success = True)
    except Exception as e:
        return MessageResponse(message = str(e), success = False)

@router.get("/scan_status", tags=["BeamScan"], response_model = ScanStatus)
async def get_ScanStatus():
    return BeamScanner.beamScanner.scanStatus
