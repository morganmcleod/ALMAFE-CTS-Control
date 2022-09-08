from fastapi import Response
from pydantic import BaseModel
from typing import Dict
from fastapi.encoders import jsonable_encoder
import json

class MessageResponse(BaseModel):
    message:str
    success:bool

class VersionResponse(BaseModel):
    name:str
    apiVersion:str
    gitCommit:str
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