# FastAPI and ASGI:
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# Imports for this app:
from Response import MessageResponse, VersionResponse, prepareResponse
from ALMAFE.common.GitVersion import gitVersion, gitBranch
from routers.CartAssembly import router as cartAssyRouter
from routers.CCA import router as ccaRouter
from routers.Database import router as databaseRouter
from routers.FEMC import router as femcRouter
from routers.LO import router as loRouter
from routers.RFSource import router as rfRouter
from routers.TemperatureMonitor import router as tempsRouter
from routers.ColdLoad import router as coldLoadRouter
from routers.MeasControl import router as measControlRouter
from routers.NoiseTemperature import router as noiseTempRouter
from routers.Stability import router as stabilityRouter
from routers.ReferenceSource import router as loRefRouter
from routers.ReferenceSource import router as rfRefRouter
from routers.BeamScanner import router as beamScanRouter
from routers.WarmIFPlate import router as warmIfRouter
from routers.ConnectionManager import ConnectionManager

# logging:
import logging
LOG_TO_FILE = True
LOG_FILE = 'ALMAFE-CTS-Control.log'

# globals:
tags_metadata = [
    {
        "name": "API",
        "description": "info about this API"
    },
    {
        "name": "BeamScan",
        "description": "beam scanner and motor controller"
    },
    {
        "name": "CartAssembly",
        "description": "coordinate action of CCA and LO"
    },
    {
        "name": "CCA",
        "description": "the cold cartridge under test"
    },
    {
        "name": "Database",
        "description": "the band 6 cartridge database"
    },
    {
        "name": "FEMC",
        "description": "front end monitor and control module"
    },
    {
        "name": "LO",
        "description": "the local oscillator"
    },
    {
        "name": "Measure",
        "description": "start and stop measurements"
    },
    {
        "name": "Noise Temp",
        "description": "Noise Temperature measurement and hardware"
    },
    {
        "name": "Stability",
        "description": "Amplitude and phase stability"
    },
    {
        "name": "RF source",
        "description": "aka BEASTs"
    },
    {
        "name": "Signal generators",
        "description": "LO and RF reference sources"
    },
    {
        "name": "Warm IF plate",
        "description": "Input switch, YIG filter, etc."
    },
    {
        "name": "Temperatures",
        "description": "Temperature Monitor"
    },
    {
        "name": "Cold load",
        "description": "Cold load fill controller"
    }
]

app = FastAPI(openapi_tags=tags_metadata)
app.include_router(beamScanRouter, tags=["BeamScan"])
app.include_router(cartAssyRouter, tags=["CartAssembly"])
app.include_router(ccaRouter, tags=["CCA"])
app.include_router(databaseRouter, tags=["Database"])
app.include_router(femcRouter, tags=["FEMC"])
app.include_router(loRouter, prefix = "/lo", tags=["LO"])
app.include_router(rfRouter, prefix = "/rfsource", tags=["RF source"])
app.include_router(tempsRouter, tags={"Temperatures"})
app.include_router(coldLoadRouter, tags={"Cold load"})
app.include_router(loRefRouter, prefix = "/loref", tags=["Signal generators"])
app.include_router(rfRefRouter, prefix = "/rfref", tags=["Signal generators"])
app.include_router(measControlRouter, tags=["Measure"])
app.include_router(noiseTempRouter, tags=["Noise Temp"])
app.include_router(stabilityRouter, tags=["Stability"])
app.include_router(warmIfRouter, tags=["Warm IF plate"])

API_VERSION = "0.0.1"

# set up CORSMiddleware to allow local development:
#TODO: this will need to be updated in the deployment environment
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["http://localhost:3000"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)


# Send a message on /startup_ws websocket to tell clients to reload
manager = ConnectionManager()
startupEvent = {'msg': 'API Startup'}

@app.websocket("/startup_ws")
async def websocket_actionPublisher(websocket: WebSocket):
    global startupEvent
    await manager.connect(websocket)
    try:
        if startupEvent:
            await manager.send(startupEvent, websocket)
            startupEvent = None
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.exception("WebSocketDisconnect: /startup_ws")

@app.get("/", tags=["API"], response_model = MessageResponse)
async def get_Root(callback:str = None):
    '''
    Hello world
    :return MessageResponse 
    '''
    result = MessageResponse(message = 'ALMAFE-CTS-Control API version ' + API_VERSION + '. See /docs', success = True)
    return prepareResponse(result, callback)

@app.get("/version", tags=["API"], response_model = VersionResponse)
async def get_API_Version(callback:str = None):
    '''
    Get the version information for this API and source code
    :param callback: optional name of Javascript function to wrap JSONP results in.
    :return VersionResponse
    '''
    branch = gitBranch()
    commit = gitVersion(branch = branch)
    result = VersionResponse(name = "ALMAFE-CTS-Control API",
                             apiVersion = API_VERSION,
                             gitBranch = branch,
                             gitCommit = commit,
                             success = True)
    return prepareResponse(result, callback)

if __name__ == "__main__":
    logger = logging.getLogger("ALMAFE-CTS-Control")
    logger.setLevel(logging.DEBUG)
    if LOG_TO_FILE:
        handler = logging.FileHandler(LOG_FILE)
    else:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt = '%(asctime)s %(levelname)s:%(message)s'))
    logger.addHandler(handler)

    logger2 = logging.getLogger("ALMAFE-AMBDeviceLibrary")
    logger2.setLevel(logging.DEBUG)
    logger2.addHandler(handler)

    logger.info("---- ALMAFE-CTS-Control start ----")

    uvicorn.run(app, host="0.0.0.0", port=8000)
