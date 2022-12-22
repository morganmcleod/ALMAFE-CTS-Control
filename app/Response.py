from fastapi import Response
from pydantic import BaseModel
from typing import Any, Dict, List
from fastapi.encoders import jsonable_encoder
import json

class KeyResponse(BaseModel):
    key:int
    message:str
    success:bool

class MessageResponse(BaseModel):
    message:str
    success:bool

class ListResponse(BaseModel):
    items:List[Any]
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

def prepareListResponse(items:List[Any] = None, callback:str = None):
    '''
    Helper function to properly format a result for return
    :param items: list or None.  If none it will be returned as []
    :param callback: optional name of Javascript function to wrap JSONP results in.
    :return FastAPI.Response or dict{items, success}
    '''
    # prepare result:
    result = ListResponse(items = items if items else [],
                          success = 'true' if items else 'false')
    return prepareResponse(result, callback)
