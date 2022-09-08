import os
import sys
from pathlib import Path
from ALMAFE.common.GitVersion import gitBranch, gitVersion

# add the top-level project path to PYTHONPATH:
thisPath = Path.cwd()
projectRoot = str(thisPath.parent)
sys.path.append(projectRoot)

# and change to that directory:
os.chdir(projectRoot)

# FastAPI and ASGI:
import uvicorn
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict
from fastapi.encoders import jsonable_encoder
import json

# globals:
app = FastAPI()
API_VERSION = "0.0.1"

# set up CORSMiddleware to allow local development:
#TODO: this will need to be updated in the deployment environment
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["http://127.0.0.1:1841"], # port used by "sencha app watch"
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)

class MessageResponse(BaseModel):
    message:str
    success:bool

def prepareResponse(result:Dict, callback:str = None):
    '''
    Helper function to properly format a result for return
    :param result: dict to convert to JSON.
    :param callback: optional name of Javascript function to wrap JSONP results in.
    :return FastAPI.Response or dict{result, success}
    '''
    # check for JSONP callback:
    if callback:
        # format and return the result as a Javascript callback:
        content = "{}({});".format(callback, json.dumps(jsonable_encoder(result)))
        return Response(content=content, media_type="text/javascript")
    else:
        # return the result in the normal FastAPI way:
        return result

@app.get("/", response_model = MessageResponse)
async def getRoot(callback:str = None):
    '''
    Hello world
    :return MessageResponse 
    '''
    global API_VERSION
    result = MessageResponse(message = 'ALMAFE-CTS-Control API version ' + API_VERSION + '. See /docs', success = True)
    return prepareResponse(result, callback)

@app.get("/app/version/")
async def getAppVersion(callback:str = None):
    '''
    Get the version string for the API server source code
    :param callback: optional name of Javascript function to wrap JSONP results in.
    :return MessageResponse
    '''
    global API_VERSION
    appVersion = 'API:' + API_VERSION + ' ' + gitVersion(branch = 'master')
        
    result = MessageResponse(message = appVersion, success = True)
    return prepareResponse(result, callback)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
