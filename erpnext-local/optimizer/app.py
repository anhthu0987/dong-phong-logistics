"""Internal optimizer. No public port, authenticated, limited one solve at a time."""
import os
import secrets
import threading
from fastapi import FastAPI, Header, HTTPException
from solver import solve, validate_payload
from osrm_routes import matrix, geometry, RoutesError

app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
lock=threading.Lock()

@app.get('/health')
def health():
    return {'status':'ok','routing_provider':'OSRM / OpenStreetMap'}

@app.post('/solve')
def optimize(data:dict,x_optimizer_token:str=Header(default='')):
    token=os.getenv('OPTIMIZER_TOKEN','')
    if not token or not secrets.compare_digest(token,x_optimizer_token):
        raise HTTPException(403,'Unauthorized')
    if not lock.acquire(blocking=False):
        raise HTTPException(429,'Dịch vụ đang tính phương án khác; thử lại sau.')
    try:
        validate_payload(data)
        seconds,meters=matrix(data)
        result=solve(data,seconds,meters)
        if result['status']=='Ready':
            geometry(data,result,seconds)
        result.update({'provider':'OSRM / OpenStreetMap','seconds':seconds,'meters':meters,
                       'traffic':'Static road speeds; no live traffic','return_to_origin':True})
        return result
    except (ValueError,KeyError,TypeError) as error:
        raise HTTPException(422,str(error)) from None
    finally:
        lock.release()
