import asyncio

# FastAPI and ASGI:
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# logging:
import logging
LOG_TO_FILE = True
LOG_FILE = 'ALMAFE-CTS-Control.log'
LOG_LEVEL = logging.INFO

logger = logging.getLogger("ALMAFE-CTS-Control")
logger.setLevel(LOG_LEVEL)
if LOG_TO_FILE:
    handler = logging.FileHandler(LOG_FILE)
else:
    handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(fmt = '%(asctime)s %(levelname)s:%(message)s'))
logger.addHandler(handler)

logger2 = logging.getLogger("ALMAFE-AMBDeviceLibrary")
logger2.setLevel(LOG_LEVEL)
logger2.addHandler(handler)

logger3 = logging.getLogger("ALMAFE-Instr")
logger3.setLevel(LOG_LEVEL)
logger3.addHandler(handler)

# Imports for this app:
from app_Common.Response import MessageResponse, VersionResponse, prepareResponse
from ALMAFE.common.GitVersion import gitVersion, gitBranch
from app_CTS.routers.CartAssembly import router as cartAssyRouter
from app_CTS.routers.CCA import router as ccaRouter
from app_CTS.routers.Chopper import router as chopperRouter
from app_CTS.routers.Database import router as databaseRouter
from app_CTS.routers.FEMC import router as femcRouter
from app_CTS.routers.LO import router as loRouter
from app_CTS.routers.RFSource import router as rfRouter
from app_CTS.routers.TemperatureMonitor import router as tempsRouter
from app_CTS.routers.ColdLoad import router as coldLoadRouter
from app_CTS.routers.SpectrumAnalyzer import router as specAnRouter
from app_CTS.routers.PowerDetect import router as powerDetectRouter
from app_CTS.routers.MeasControl import router as measControlRouter
from app_CTS.routers.NoiseTemperature import router as noiseTempRouter
from app_CTS.routers.Stability import router as stabilityRouter
from app_CTS.routers.ReferenceSource import router as loRefRouter
from app_CTS.routers.ReferenceSource import router as rfRefRouter
from app_CTS.routers.BeamScanner import router as beamScanRouter
from app_CTS.routers.IFSystem import router as ifSystemRouter
from app_CTS.routers.DataDisplay import router as dataDisplayRouter
from app_CTS.routers.MixerTests import router as mixerTestsRouter
from app_CTS.routers.ConnectionManager import ConnectionManager




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
        "name": "Chopper",
        "description": "the cold load chopper"
    },
    {
        "name": "Cold load",
        "description": "Cold load fill controller"
    },
    {
        "name": "Data display",
        "description": "Real-time data for the user interface"
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
        "name": "Mixer tests",
        "description": "I-V curves, magnet optimization, mixers deflux"
    },
    {
        "name": "Noise temp",
        "description": "Noise Temperature measurement and hardware"
    },
    {
        "name": "Power detection",
        "description": "Power detection"
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
        "name": "SpecAn",
        "description": "Spectrum analyzer"
    },
    {
        "name": "Stability",
        "description": "Amplitude and phase stability"
    },
    {
        "name": "Temperatures",
        "description": "Temperature Monitor"
    },
    {
        "name": "IF system",
        "description": "Input switch, YIG filter, etc."
    }
]

app = FastAPI(openapi_tags=tags_metadata)
app.include_router(beamScanRouter, tags=["BeamScan"])
app.include_router(cartAssyRouter, tags=["CartAssembly"])
app.include_router(ccaRouter, tags=["CCA"])
app.include_router(chopperRouter, tags=["Chopper"])
app.include_router(databaseRouter, tags=["Database"])
app.include_router(femcRouter, tags=["FEMC"])
app.include_router(loRouter, prefix = "/lo", tags=["LO"])
app.include_router(rfRouter, prefix = "/rfsource", tags=["RF source"])
app.include_router(tempsRouter, tags={"Temperatures"})
app.include_router(coldLoadRouter, tags={"Cold load"})
app.include_router(specAnRouter, tags = ["SpecAn"])
app.include_router(powerDetectRouter, tags = ["Power detection"])
app.include_router(loRefRouter, prefix = "/loref", tags=["Signal generators"])
app.include_router(rfRefRouter, prefix = "/rfref", tags=["Signal generators"])
app.include_router(measControlRouter, tags=["Measure"])
app.include_router(noiseTempRouter, tags=["Noise temp"])
app.include_router(stabilityRouter, tags=["Stability"])
app.include_router(ifSystemRouter, tags=["IF system"])
app.include_router(dataDisplayRouter, tags=["Data display"])
app.include_router(mixerTestsRouter, tags=["Mixer tests"])

API_VERSION = "0.0.1"

# set up CORSMiddleware to allow local development:
#TODO: this will need to be updated in the deployment environment
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["http://localhost:3000"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
    expose_headers = ["content-disposition"]
)

# Send a message on /startup_ws websocket to tell clients to reload
manager = ConnectionManager()
startupEvent = {'msg': 'API Startup'}

@app.websocket("/startup_ws")
async def websocket_actionPublisher(websocket: WebSocket):
    global startupEvent
    await manager.connect(websocket)
    while True:
        try:
            if startupEvent:
                await manager.send(startupEvent, websocket)
                startupEvent = None
        except WebSocketDisconnect:
            manager.disconnect(websocket)
            logger.exception("WebSocketDisconnect: /startup_ws")
        await asyncio.sleep(1)

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
    logger.info("---- ALMAFE-CTS-Control start ----")
    uvicorn.run(app, host="0.0.0.0", port=8000)
