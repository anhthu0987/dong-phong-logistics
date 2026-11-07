"""Server-side rules. Submitted, unfinished trips reserve vehicle and driver.

Drafts are plans, not reservations. Intervals use [start, end).
Master row locks serialize submissions sharing a vehicle or driver.
"""
import math
import frappe
from frappe.utils import flt, get_datetime, getdate

def fail(code, message):
    frappe.throw(f'[{code}] {message}')

def number(value, label):
    n=flt(value)
    if not math.isfinite(n) or n<0:
        fail('DP_NUMBER',label+' phải là số không âm hợp lệ.')
    return n

def validate_vehicle(doc, method=None):
    number(doc.get('custom_payload_capacity_kg'),'Tải trọng xe')

def validate_odometer(doc, method=None):
    start=number(doc.get('custom_start_odometer'),'Số km đầu chuyến')
    end=number(doc.get('custom_end_odometer'),'Số km cuối chuyến')
    if end and end<start:
        fail('DP_ODOMETER','Số km cuối chuyến phải lớn hơn hoặc bằng số km đầu chuyến.')

def apply_delivery_order_totals(doc, method=None):
    assigned = [row.get('custom_delivery_order') for row in doc.delivery_stops if row.get('custom_delivery_order')]
    if len(assigned) != len(set(assigned)):
        fail('DP_DUPLICATE_ORDER','Không gắn cùng một đơn giao hai lần trong một chuyến.')
    total_weight = 0
    quantities = {}
    for stop in doc.delivery_stops:
        order_name=stop.get('custom_delivery_order')
        if not order_name:
            continue
        order = frappe.get_doc('Delivery Order', order_name)
        if order.docstatus != 1:
            fail('DP_ORDER_DRAFT','Chỉ phân đơn giao đã được xác nhận.')
        if not order.shipping_address:
            fail('DP_ORDER_ADDRESS','Đơn giao chưa có địa chỉ nhận được tạo. Hãy mở và Submit lại đơn.')
        stop.customer=order.customer
        stop.address=order.shipping_address
        stop.customer_address=order.delivery_address
        other_trip = frappe.db.sql('''SELECT trip.name FROM `tabDelivery Trip` trip
            INNER JOIN `tabDelivery Stop` stop ON stop.parent=trip.name
            WHERE stop.custom_delivery_order=%s AND trip.name!=%s AND trip.docstatus=1
            AND trip.status IN ('Scheduled','In Transit') LIMIT 1''',(order_name,doc.name or ''),as_dict=True)
        if other_trip:
            fail('DP_ORDER_ASSIGNED',f'Đơn {order_name} đã thuộc chuyến {other_trip[0].name}.')
        for item in order.items:
            total_weight += flt(item.qty) * flt(item.weight_kg)
            unit = item.uom or 'kiện'
            quantities[unit] = quantities.get(unit, 0) + flt(item.qty)
        if (doc.docstatus==1 or method=='before_submit') and order.delivery_status in ('Draft','Pending Assignment'):
            frappe.db.set_value('Delivery Order',order_name,'delivery_status','Assigned',update_modified=False)
    if assigned:
        if total_weight <= 0:
            fail('DP_ORDER_WEIGHT','Các đơn được phân phải có khối lượng hàng hợp lệ.')
        doc.custom_planned_load_kg = total_weight
        doc.custom_total_delivery_qty = ' + '.join(f'{qty:g} {unit}' for unit,qty in sorted(quantities.items()))
    else:
        doc.custom_total_delivery_qty = None

def validate_trip(doc, method=None):
    if doc.docstatus==2: return
    old=doc.get_doc_before_save()
    if doc.status=='Completed' and (not doc.get('custom_completed_at') or doc.get('custom_completion_status') not in ('Approved','Exception Closed')):
        fail('DP_COMPLETION_APPROVAL','Chuyến chỉ được đánh dấu hoàn tất sau khi Admin duyệt hoàn tất hoặc đóng theo diện sự cố.')
    if old:
        for field in ('custom_completion_status','custom_completion_requested_at','custom_completion_requested_by','custom_completed_at','custom_completed_by','custom_completion_review_note'):
            if (doc.get(field) or None)!=(old.get(field) or None) and frappe.flags.get('dp_trip_action')!=doc.name:
                fail('DP_COMPLETION_APPROVAL','Dùng nút yêu cầu/duyệt hoàn tất chuyến để thay đổi trạng thái kết thúc.')
        if doc.status=='Completed' and old.status!='Completed' and frappe.flags.get('dp_trip_action')!=doc.name:
            fail('DP_COMPLETION_APPROVAL','Chuyến chỉ được chuyển Completed sau khi quản trị viên duyệt.')
    elif (doc.get('custom_completed_at') or doc.get('custom_completion_requested_at') or doc.get('custom_completion_status') not in (None,'','Open')) and frappe.flags.get('dp_trip_action')!=doc.name:
        fail('DP_COMPLETION_APPROVAL','Không được tự đặt trạng thái duyệt khi tạo chuyến.')
    apply_delivery_order_totals(doc,method)
    validate_odometer(doc)
    load=number(doc.get('custom_planned_load_kg'),'Khối lượng dự kiến')
    start=get_datetime(doc.departure_time) if doc.departure_time else None
    end=get_datetime(doc.custom_expected_end_time) if doc.get('custom_expected_end_time') else None
    submitting=doc.docstatus==1 or method=='before_submit'
    if start and end and end<=start:
        fail('DP_TIME','Giờ kết thúc dự kiến phải sau giờ xuất phát.')
    if submitting and (not start or not end or not doc.driver):
        fail('DP_REQUIRED','Cần tài xế, giờ xuất phát và giờ kết thúc dự kiến trước khi xác nhận chuyến.')
    # Lock master rows even for draft validation so submit checks use fresh data.
    vehicles=frappe.db.sql('SELECT name, custom_technical_status, custom_payload_capacity_kg FROM `tabVehicle` WHERE name=%s FOR UPDATE',doc.vehicle,as_dict=True)
    if not vehicles: fail('DP_VEHICLE','Xe không tồn tại.')
    vehicle=vehicles[0]
    doc.custom_vehicle_capacity_kg=flt(vehicle.custom_payload_capacity_kg)
    if vehicle.custom_technical_status not in (None,'','Available'):
        fail('DP_UNAVAILABLE','Xe đang bảo trì hoặc ngừng hoạt động, không thể phân công.')
    if submitting and vehicle.custom_technical_status!='Available':
        fail('DP_UNCONFIRMED','Cần xác nhận tình trạng xe là Available trước khi xác nhận chuyến.')
    capacity=number(vehicle.custom_payload_capacity_kg,'Tải trọng xe')
    if submitting and (capacity<=0 or load<=0):
        fail('DP_LOAD_REQUIRED','Cần khai báo tải trọng xe và khối lượng hàng dự kiến lớn hơn 0.')
    if capacity and load>capacity:
        fail('DP_OVERLOAD','Khối lượng hàng dự kiến vượt tải trọng của xe.')
    if doc.driver:
        drivers=frappe.db.sql('SELECT name,status,expiry_date FROM `tabDriver` WHERE name=%s FOR UPDATE',doc.driver,as_dict=True)
        if not drivers or drivers[0].status!='Active':
            fail('DP_DRIVER','Tài xế phải có trạng thái Active.')
        if drivers[0].expiry_date and start and getdate(drivers[0].expiry_date)<getdate(end or start):
            fail('DP_LICENSE','Giấy phép tài xế hết hạn trước khi chuyến dự kiến kết thúc.')
    if not start or not end: return
    # Locking read avoids a stale REPEATABLE READ snapshot after waiting on a master lock.
    conflicts=frappe.db.sql('''SELECT name, vehicle, driver FROM `tabDelivery Trip`
        WHERE name != %s AND docstatus=1 AND status IN ('Scheduled','In Transit')
        AND (vehicle=%s OR (%s != '' AND driver=%s))
        AND departure_time < %s
        AND (custom_expected_end_time IS NULL OR custom_expected_end_time > %s)
        FOR UPDATE''',(doc.name or '',doc.vehicle,doc.driver or '',doc.driver or '',end,start),as_dict=True)
    if conflicts:
        c=conflicts[0]
        resource='Xe' if c.vehicle==doc.vehicle else 'Tài xế'
        fail('DP_CONFLICT',resource+' đã có chuyến được xác nhận trùng khoảng thời gian. Hãy chọn thời gian hoặc nguồn lực khác.')
