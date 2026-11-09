"""Versioned planning, background optimization and atomic release."""
import hashlib
import json
import math
import uuid
import requests
import frappe
from frappe.utils import get_datetime, now_datetime, add_to_date, flt

PROTECTED=('status','version','snapshot','input_hash','proposal','run_token','requested_by','requested_at','computed_at','approved_by','approved_at','published_trips','error_message','review_note')

def fail(text): frappe.throw('[DP_PLAN] '+text)
def dumps(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,default=str)
def digest(x):return hashlib.sha256(dumps(x).encode()).hexdigest()
def authorize():
    if frappe.session.user!='Administrator' and not set(frappe.get_roles()) & {'System Manager','Fleet Manager'}:
        frappe.throw('Chỉ điều phối viên được lập/duyệt kế hoạch.',frappe.PermissionError)
def locked(name):
    frappe.db.sql('SELECT name FROM `tabTransport Plan` WHERE name=%s FOR UPDATE',name)
    return frappe.get_doc('Transport Plan',name)
def update(plan,**values):
    for k,v in values.items():plan.set(k,v)
    previous=frappe.flags.get('planning_internal')
    frappe.flags.planning_internal=plan.name
    try:plan.save(ignore_permissions=True)
    finally:frappe.flags.planning_internal=previous

def validate_plan(doc,method=None):
    old=doc.get_doc_before_save()
    if frappe.flags.get('planning_internal')!=doc.name:
        authorize()
        if old and old.status!='Draft':fail('Kế hoạch đã gửi tính không được sửa; tạo phiên bản mới bằng nút Tính lại.')
        for key in PROTECTED:
            expected=old.get(key) if old else ('Draft' if key=='status' else (0 if key=='version' else None))
            if (doc.get(key) or None)!=(expected or None):fail('Dùng các nút nghiệp vụ để thay đổi trạng thái/phương án.')
    if not 1<=len(doc.orders)<=10 or not 1<=len(doc.vehicles)<=5:fail('Chọn 1–10 đơn và 1–5 xe.')
    if len({r.delivery_order for r in doc.orders})!=len(doc.orders):fail('Đơn bị lặp.')
    if len({r.vehicle for r in doc.vehicles})!=len(doc.vehicles) or len({r.driver for r in doc.vehicles})!=len(doc.vehicles):fail('Xe/tài xế bị lặp.')

def snapshot(plan):
    start,end=map(get_datetime,(plan.departure,plan.end_time))
    horizon=int((end-start).total_seconds())
    if not 0<horizon<=172800:fail('Khoảng kế hoạch phải dương và tối đa 48 giờ.')
    data=dict(company=plan.company,departure=str(start),horizon=horizon,orders=[],vehicles=[])
    for row in sorted(plan.orders,key=lambda r:r.delivery_order):
        frappe.db.sql('SELECT name FROM `tabDelivery Order` WHERE name=%s FOR UPDATE',row.delivery_order)
        o=frappe.get_doc('Delivery Order',row.delivery_order)
        if o.docstatus!=1 or o.delivery_status not in ('Pending Assignment','Assigned'):fail('Đơn không còn sẵn sàng phân chuyến: '+o.name)
        if frappe.db.get_value('Quotation',o.quotation,'company')!=plan.company:fail('Đơn thuộc công ty khác.')
        if frappe.db.sql('''SELECT t.name FROM `tabDelivery Trip` t JOIN `tabDelivery Stop` s ON s.parent=t.name
            WHERE t.docstatus=1 AND s.custom_delivery_order=%s LIMIT 1 FOR UPDATE''',o.name):fail('Đơn đã có chuyến: '+o.name)
        item=dict(name=o.name,weight=math.ceil(flt(o.total_weight_kg)*1000),vehicle_type=o.get('custom_required_vehicle_type') or '')
        for kind,addr in [('pickup',o.pickup_address_link),('delivery',o.shipping_address)]:
            a=frappe.get_doc('Address',addr)
            lat,lng=flt(a.custom_latitude),flt(a.custom_longitude)
            if not a.get('custom_routing_confirmed') or not -90<=lat<=90 or not -180<=lng<=180:fail('Cần kiểm tra tọa độ địa chỉ và đánh dấu xác nhận: '+addr)
            lo,hi=o.get(kind+'_window_start'),o.get(kind+'_window_end')
            if not lo or not hi:fail('Đơn thiếu khung giờ: '+o.name)
            window=[max(0,math.ceil((get_datetime(lo)-start).total_seconds())),min(horizon,int((get_datetime(hi)-start).total_seconds()))]
            if window[0]>window[1]:fail('Khung giờ đơn nằm ngoài kế hoạch.')
            item[kind]=dict(lat=lat,lng=lng,address=addr,window=window,service=math.ceil(flt(o.get(kind+'_service_minutes'))*60))
        data['orders'].append(item)
    for row in sorted(plan.vehicles,key=lambda r:r.vehicle):
        frappe.db.sql('SELECT name FROM `tabVehicle` WHERE name=%s FOR UPDATE',row.vehicle)
        frappe.db.sql('SELECT name FROM `tabDriver` WHERE name=%s FOR UPDATE',row.driver)
        v=frappe.get_doc('Vehicle',row.vehicle);d=frappe.get_doc('Driver',row.driver)
        if v.custom_technical_status!='Available' or d.status!='Active':fail('Xe/tài xế không sẵn sàng.')
        if d.expiry_date and get_datetime(str(d.expiry_date)+' 23:59:59')<end:fail('Giấy phép tài xế hết hạn trong kế hoạch.')
        if not row.origin_confirmed:fail('Xác nhận tọa độ xuất phát của xe.')
        if frappe.db.sql('''SELECT name FROM `tabDelivery Trip` WHERE docstatus=1 AND status IN ('Scheduled','In Transit')
            AND (vehicle=%s OR driver=%s) AND departure_time<%s AND (custom_expected_end_time IS NULL OR custom_expected_end_time>%s) FOR UPDATE''',(v.name,d.name,end,start)):fail('Xe/tài xế trùng lịch.')
        data['vehicles'].append(dict(name=v.name,driver=d.name,capacity=math.floor(flt(v.custom_payload_capacity_kg)*1000),
            vehicle_type=v.get('custom_routing_vehicle_type') or '',origin=dict(lat=flt(row.origin_lat),lng=flt(row.origin_lng)),odometer=flt(v.last_odometer)))
    return data

@frappe.whitelist(methods=['POST'])
def request_plan(name):
    authorize();p=locked(name);p.check_permission('write')
    if p.status not in ('Draft','Failed','Infeasible'):fail('Không thể tính ở trạng thái hiện tại.')
    if get_datetime(p.departure)<=now_datetime():fail('Giờ xuất phát phải trong tương lai.')
    
    for row in p.orders:frappe.get_doc('Delivery Order',row.delivery_order).check_permission('read')
    for row in p.vehicles:
        frappe.get_doc('Vehicle',row.vehicle).check_permission('read')
        frappe.get_doc('Driver',row.driver).check_permission('read')
    data=snapshot(p);token=uuid.uuid4().hex
    update(p,status='Queued',version=int(p.version or 0)+1,snapshot=dumps(data),input_hash=digest(data),run_token=token,
           proposal=None,published_trips=None,error_message=None,requested_by=frappe.session.user,requested_at=now_datetime())
    frappe.enqueue('dp_dispatch.planning.compute',queue='long',timeout=300,name=p.name,token=token,enqueue_after_commit=True)
    return p.name

def compute(name,token):
    p=locked(name)
    if p.run_token!=token or p.status!='Queued':return
    data=json.loads(p.snapshot)
    update(p,status='Computing');frappe.db.commit()
    try:
        secret=frappe.conf.get('optimizer_token')
        if not secret:raise ValueError('Chưa cấu hình token dịch vụ tối ưu.')
        response=requests.post('http://optimizer:8000/solve',json=data,headers={'X-Optimizer-Token':secret},timeout=(5,240))
        if response.status_code!=200:
            detail=response.json().get('detail','Dịch vụ tối ưu lỗi')
            raise ValueError(str(detail)[:500])
        result=response.json()
        if result.get('status')=='Ready':validate_result(data,result)
        elif result.get('status')!='Infeasible':raise ValueError('Trạng thái phương án không hợp lệ.')
        p=locked(name)
        if p.run_token!=token or p.status!='Computing':return
        update(p,status=result['status'],proposal=dumps(result),computed_at=now_datetime(),error_message=result.get('reason'))
    except Exception as exc:
        frappe.db.rollback();p=locked(name)
        if p.run_token==token and p.status=='Computing':update(p,status='Failed',error_message=str(exc)[:500])
    frappe.db.commit()

def validate_result(data,result):
    if result.get('provider')!='OSRM / OpenStreetMap':fail('Phương án phải dùng OSRM nội bộ.')
    orders={o['name']:o for o in data['orders']};vehicles={v['name']:v for v in data['vehicles']}
    seen=set();used=set();nv=len(vehicles);index={o['name']:nv+i*2 for i,o in enumerate(data['orders'])}
    seconds=result['seconds'];n=nv+2*len(orders)
    if len(seconds)!=n or any(len(r)!=n or any(type(x)!=int or x<0 for x in r) for r in seconds):fail('Ma trận không hợp lệ.')
    for route in result['routes']:
        v=vehicles.get(route['vehicle'])
        if not v or v['name'] in used:fail('Phương án lặp xe hoặc dùng xe ngoài lựa chọn.')
        used.add(v['name']);load=0;onboard=set();clock=0;prev=list(vehicles).index(v['name'])
        if not route['stops'] or len(route.get('segments',[]))!=len(route['stops'])+1:fail('Thiếu tuyến đường đã tính.')
        for segment in route['segments']:
            geometry=segment.get('geometry',{})
            coords=geometry.get('coordinates',[])
            if geometry.get('type')!='LineString' or len(coords)<2 or any(len(c)!=2 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in c) for c in coords):fail('Hình dạng tuyến không hợp lệ.')
        for stop in route['stops']:
            o=orders.get(stop['order']);kind=stop['kind']
            if not o or kind not in ('pickup','delivery') or (o['name'],kind) in seen:fail('Điểm lấy/giao không hợp lệ.')
            if o.get('vehicle_type') and o['vehicle_type']!=v.get('vehicle_type'):fail('Xe không đúng yêu cầu hàng.')
            node=index[o['name']]+int(kind=='delivery');point=o[kind];arrival=stop['arrival']
            if stop['node']!=node or not point['window'][0]<=arrival<=point['window'][1] or arrival<clock+seconds[prev][node]:fail('Thời gian tuyến không khả thi.')
            if kind=='pickup':onboard.add(o['name']);load+=o['weight']
            else:
                if o['name'] not in onboard:fail('Giao trước lấy hoặc khác xe.')
                onboard.remove(o['name']);load-=o['weight']
            if not 0<=load<=v['capacity'] or stop['load']!=load:fail('Tải theo chặng không hợp lệ.')
            seen.add((o['name'],kind));clock=arrival+point['service'];prev=node
        if onboard or route['end']<clock+seconds[prev][list(vehicles).index(v['name'])] or route['end']>data['horizon']:fail('Giờ về xe không hợp lệ.')
    if seen!={(o,k) for o in orders for k in ('pickup','delivery')}:fail('Phương án bỏ sót đơn.')

@frappe.whitelist(methods=['POST'])
def reset_plan(name):
    authorize();p=locked(name);p.check_permission('write')
    if p.status=='Released':fail('Kế hoạch đã phát hành không được sửa.')
    update(p,status='Draft',run_token=None,proposal=None,snapshot=None,input_hash=None,error_message=None)
    return p.name

@frappe.whitelist(methods=['POST'])
def reject_plan(name,note):
    authorize();p=locked(name);p.check_permission('write')
    if p.status!='Ready' or not (note or '').strip():fail('Chỉ từ chối phương án chờ duyệt và cần lý do.')
    update(p,status='Rejected',review_note=note)

@frappe.whitelist(methods=['POST'])
def approve_plan(name):
    authorize();p=locked(name);p.check_permission('write')
    if p.status=='Released':return json.loads(p.published_trips)
    if p.status!='Ready':fail('Chỉ duyệt phương án đã tính xong.')
    if get_datetime(p.departure)<=now_datetime():fail('Đã quá giờ xuất phát, cần tính lại.')
    data=snapshot(p)
    if digest(data)!=p.input_hash:fail('Dữ liệu đơn/xe/địa chỉ đã thay đổi; tính lại kế hoạch.')
    result=json.loads(p.proposal);validate_result(data,result)
    vehicles={v['name']:v for v in data['vehicles']};trips=[]
    from dp_dispatch.transport import order_stops
    for route in result['routes']:
        v=vehicles[route['vehicle']];stops=[]
        for s in route['stops']:
            pair=order_stops(s['order']);stop=pair[0 if s['kind']=='pickup' else 1]
            stop['custom_planned_arrival']=add_to_date(p.departure,seconds=s['arrival'])
            stops.append(stop)
        t=frappe.get_doc(dict(doctype='Delivery Trip',company=p.company,vehicle=v['name'],driver=v['driver'],
            departure_time=p.departure,custom_expected_end_time=add_to_date(p.departure,seconds=route['end']),
            custom_start_odometer=v['odometer'],custom_origin_lat=v['origin']['lat'],custom_origin_lng=v['origin']['lng'],
            custom_transport_mode='Pickup and Delivery',custom_transport_plan=p.name,custom_plan_version=p.version,
            custom_planned_route=dumps(route),delivery_stops=stops))
        previous=frappe.flags.get('plan_release');frappe.flags.plan_release=p.name
        try:t.insert();t.submit()
        finally:frappe.flags.plan_release=previous
        trips.append(t.name)
    update(p,status='Released',approved_by=frappe.session.user,approved_at=now_datetime(),published_trips=dumps(trips))
    return trips

def require_plan(doc,method=None):
    old=doc.get_doc_before_save()
    if old and old.docstatus==1:return
    if frappe.flags.get('plan_release') and doc.get('custom_transport_plan')==frappe.flags.plan_release:return
    fail('Chuyến mới phải được phát hành từ Transport Plan đã duyệt.')
