# FastAPI and ASGI:
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Imports for this app:
from Response import MessageResponse, VersionResponse, prepareResponse
from ALMAFE.common.GitVersion import gitVersion
from routers.CCA import router as ccaRouter
from routers.LO import router as loRouter
from routers.LO import router as rfRouter
from routers.ReferenceSource import router as loRefRouter
from routers.ReferenceSource import router as rfRefRouter
from routers.BeamScanner import router as beamScanRouter
from routers.WarmIFPlate import router as warmIfRouter
from routers.Database import router as databaseRouter

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
        "name": "CCA",
        "description": "the cold cartridge under test"
    },
    {
        "name": "LO",
        "description": "the local oscillator"
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
        "name": "Database",
        "description": "the band 6 cartridge database"
    }
]

app = FastAPI(openapi_tags=tags_metadata)
app.include_router(ccaRouter, tags=["CCA"])
app.include_router(loRouter, prefix = "/lo", tags=["LO"])
app.include_router(rfRouter, prefix = "/rfsource", tags=["RF source"])
app.include_router(loRefRouter, prefix = "/loref", tags=["Signal generators"])
app.include_router(rfRefRouter, prefix = "/rfref", tags=["Signal generators"])
app.include_router(beamScanRouter, tags=["BeamScan"])
app.include_router(warmIfRouter, tags=["Warm IF plate"])
app.include_router(databaseRouter, tags=["Database"])

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

@app.get("/", tags=["API"], response_model = MessageResponse)
async def get_Root(callback:str = None):
    '''
    Hello world
    :return MessageResponse 
    '''
    global API_VERSION
    result = MessageResponse(message = 'ALMAFE-CTS-Control API version ' + API_VERSION + '. See /docs', success = True)
    return prepareResponse(result, callback)

@app.get("/version", tags=["API"], response_model = VersionResponse)
async def get_API_Version(callback:str = None):
    '''
    Get the version information for this API and source code
    :param callback: optional name of Javascript function to wrap JSONP results in.
    :return VersionResponse
    '''
    global API_VERSION
    result = VersionResponse(name = "ALMAFE-CTS-Control API",
                             apiVersion = API_VERSION,
                             gitCommit = gitVersion(branch = 'master'),
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
