import os
import sys
from pathlib import Path

# FastAPI and ASGI:
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# add the top-level project path to PYTHONPATH:
projectRoot = Path.cwd()
sys.path.append(projectRoot)
sys.path.append("L:\\Python\\ALMAFE-Lib")
sys.path.append("L:\\Python\\ALMAFE-AMBDeviceLibrary")

# and change to that directory:
os.chdir(projectRoot)

# Imports for this app:
from Response import MessageResponse, VersionResponse, prepareResponse
from ALMAFE.common.GitVersion import gitVersion
from routers.CCA import router as ccaRouter
from routers.LO import router as loRouter
from routers.RFSource import router as srcRouter

# globals:

tags_metadata = [
    {
        "name": "API",
        "description": "info about this API"
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
    }
]

app = FastAPI(openapi_tags=tags_metadata)
app.include_router(ccaRouter)
app.include_router(loRouter)
app.include_router(srcRouter)

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
    uvicorn.run(app, host="0.0.0.0", port=8000)
