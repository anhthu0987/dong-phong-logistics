"""Mandatory pickup-delivery VRP. Integer grams/seconds/meters, no dropped orders."""
import math
from ortools.constraint_solver import pywrapcp, routing_enums_pb2


def validate_payload(data):
    orders, vehicles = data['orders'], data['vehicles']
    if not 1 <= len(orders) <= 10 or not 1 <= len(vehicles) <= 5:
        raise ValueError('Mỗi kế hoạch cần 1–10 đơn và 1–5 xe.')
    horizon = data['horizon']
    if not isinstance(horizon, int) or not 1 <= horizon <= 172800:
        raise ValueError('Thời gian kế hoạch tối đa 48 giờ.')
    if len({o['name'] for o in orders}) != len(orders) or len({v['name'] for v in vehicles}) != len(vehicles):
        raise ValueError('Đơn hoặc xe bị lặp.')
    for v in vehicles:
        if not isinstance(v['capacity'], int) or v['capacity'] <= 0:
            raise ValueError('Tải trọng xe không hợp lệ.')
    for o in orders:
        if not isinstance(o['weight'], int) or o['weight'] <= 0:
            raise ValueError('Khối lượng đơn không hợp lệ.')
        for kind in ('pickup', 'delivery'):
            p = o[kind]
            if not 0 <= p['window'][0] <= p['window'][1] <= horizon or not 0 <= p['service'] <= horizon:
                raise ValueError('Khung giờ hoặc thời gian phục vụ không hợp lệ.')
    points = [v['origin'] for v in vehicles] + [o[k] for o in orders for k in ('pickup', 'delivery')]
    for p in points:
        if any(not math.isfinite(float(p[k])) for k in ('lat', 'lng')) or not -90 <= p['lat'] <= 90 or not -180 <= p['lng'] <= 180:
            raise ValueError('Tọa độ không hợp lệ.')
    return points


def solve(data, seconds, meters):
    points = validate_payload(data)
    n, nv, horizon = len(points), len(data['vehicles']), data['horizon']
    for matrix in (seconds, meters):
        if len(matrix) != n or any(len(row) != n for row in matrix):
            raise ValueError('Thiếu ma trận đường đi.')
        if any(not isinstance(x, int) or x < 0 for row in matrix for x in row):
            raise ValueError('Đường đi bị thiếu/lỗi, không được thay bằng 0.')
    manager = pywrapcp.RoutingIndexManager(n, nv, list(range(nv)), list(range(nv)))
    routing = pywrapcp.RoutingModel(manager)
    service = [0] * nv + [o[k]['service'] for o in data['orders'] for k in ('pickup','delivery')]
    demand = [0] * nv + [d for o in data['orders'] for d in (o['weight'], -o['weight'])]
    def transit(a, b):
        a,b=manager.IndexToNode(a),manager.IndexToNode(b)
        return service[a] + seconds[a][b]
    transit_idx=routing.RegisterTransitCallback(transit)
    routing.SetArcCostEvaluatorOfAllVehicles(routing.RegisterTransitCallback(lambda a,b: seconds[manager.IndexToNode(a)][manager.IndexToNode(b)]))
    routing.AddDimension(transit_idx, horizon, horizon, True, 'Time')
    time=routing.GetDimensionOrDie('Time')
    demand_idx=routing.RegisterUnaryTransitCallback(lambda a:demand[manager.IndexToNode(a)])
    routing.AddDimensionWithVehicleCapacity(demand_idx,0,[v['capacity'] for v in data['vehicles']],True,'Load')
    for i,o in enumerate(data['orders']):
        pi,di=nv+2*i,nv+2*i+1
        p,d=manager.NodeToIndex(pi),manager.NodeToIndex(di)
        routing.AddPickupAndDelivery(p,d)
        routing.solver().Add(routing.VehicleVar(p)==routing.VehicleVar(d))
        routing.solver().Add(time.CumulVar(p)<=time.CumulVar(d))
        allowed=[vi for vi,v in enumerate(data['vehicles']) if not o.get('vehicle_type') or o['vehicle_type']==v.get('vehicle_type')]
        if not allowed:
            return {'status':'Infeasible','routes':[], 'reason':f"Không có xe phù hợp loại hàng cho đơn {o['name']}."}
        routing.SetAllowedVehiclesForIndex(allowed,p); routing.SetAllowedVehiclesForIndex(allowed,d)
        for idx,key in ((p,'pickup'),(d,'delivery')):
            time.CumulVar(idx).SetRange(*o[key]['window'])
            routing.AddVariableMinimizedByFinalizer(time.CumulVar(idx))
    for v in range(nv):
        routing.AddVariableMinimizedByFinalizer(time.CumulVar(routing.End(v)))
    params=pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy=routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    params.local_search_metaheuristic=routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds=5
    solution=routing.SolveWithParameters(params)
    if not solution:
        return {'status':'Infeasible','routes':[], 'reason':'Không tìm được phương án trong giới hạn tính toán. Kiểm tra tải trọng/khung giờ; chưa chứng minh bài toán vô nghiệm.'}
    routes=[]
    for v in range(nv):
        idx=routing.Start(v); stops=[]; load=0; distance=0; driving=0
        while not routing.IsEnd(idx):
            nxt=solution.Value(routing.NextVar(idx))
            a,b=manager.IndexToNode(idx),manager.IndexToNode(nxt)
            distance+=meters[a][b];driving+=seconds[a][b]
            if a>=nv:
                oi=(a-nv)//2; kind='pickup' if (a-nv)%2==0 else 'delivery'
                load+=demand[a]
                stops.append({'order':data['orders'][oi]['name'],'kind':kind,'node':a,
                              'arrival':solution.Value(time.CumulVar(idx)), 'load':load})
            idx=nxt
        if stops:
            routes.append({'vehicle':data['vehicles'][v]['name'],'stops':stops,
                           'end':solution.Value(time.CumulVar(idx)), 'distance_m':distance,'driving_s':driving})
    return {'status':'Ready','routes':routes, 'reason':''}
