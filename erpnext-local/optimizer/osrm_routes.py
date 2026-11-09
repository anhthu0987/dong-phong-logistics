"""Self-hosted OSRM adapter. No public fallback, no fabricated missing routes."""
import math
import os
import requests
from solver import validate_payload

class RoutesError(ValueError):
    pass


def call(service, points, **params):
    base=os.environ.get('OSRM_URL','http://osrm:5000').rstrip('/')
    coords=';'.join(f"{p['lng']:.7f},{p['lat']:.7f}" for p in points)
    params['radiuses']=';'.join(['1000']*len(points))
    try:
        response=requests.get(f'{base}/{service}/v1/driving/{coords}',params=params,timeout=(5,40))
        data=response.json()
    except (requests.RequestException,ValueError):
        raise RoutesError('Không kết nối được OSRM nội bộ. Kiểm tra dịch vụ và dữ liệu bản đồ.') from None
    if response.status_code!=200 or data.get('code')!='Ok':
        raise RoutesError('OSRM không tìm được đường cho các điểm đã chọn; kiểm tra tọa độ và phạm vi bản đồ.')
    return data


def number(value):
    if value is None or not isinstance(value,(float,int)) or not math.isfinite(value) or value<0:
        raise RoutesError('Ma trận có chặng thiếu hoặc không hợp lệ; không được thay bằng đường chim bay.')
    return math.ceil(value)


def matrix(data):
    points=validate_payload(data)
    response=call('table',points,annotations='duration,distance')
    n=len(points)
    matrices=[]
    for key in ('durations','distances'):
        matrix=response.get(key)
        if not matrix or len(matrix)!=n or any(len(row)!=n for row in matrix):
            raise RoutesError('OSRM trả thiếu ma trận đường đi.')
        matrices.append([[number(value) for value in row] for row in matrix])
    return tuple(matrices)


def geometry(data,result,seconds):
    points=validate_payload(data)
    vehicles={v['name']:i for i,v in enumerate(data['vehicles'])}
    for route in result['routes']:
        start=vehicles[route['vehicle']]
        indexes=[start]+[s['node'] for s in route['stops']]+[start]
        segments=[]
        for a,b in zip(indexes,indexes[1:]):
            response=call('route',[points[a],points[b]],overview='full',geometries='geojson',steps='false')
            options=response.get('routes') or []
            if not options or not options[0].get('geometry',{}).get('coordinates'):
                raise RoutesError('Thiếu hình dạng tuyến đường dự kiến.')
            leg=options[0]
            if number(leg['duration']) > seconds[a][b]+1:
                raise RoutesError('Thời gian tuyến khác ma trận; hãy tính lại.')
            segments.append({'from_node':a,'to_node':b,'geometry':leg['geometry'],
                             'duration':number(leg['duration']),'distance_m':number(leg['distance'])})
        route['segments']=segments
