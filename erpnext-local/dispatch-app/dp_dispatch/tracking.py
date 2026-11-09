"""Trip-scoped tracking; operational mutations stay in completion/confirmation."""
import frappe
from frappe.utils import cint, flt

from dp_dispatch.permissions import driver_for_user, is_driver


def require_reader():
    roles = set(frappe.get_roles())
    if frappe.session.user == 'Guest' or not (
        frappe.session.user == 'Administrator' or roles & {'System Manager', 'Fleet Manager', 'DP Driver'}
    ):
        frappe.throw('Bạn không có quyền theo dõi chuyến.', frappe.PermissionError)


def readable_trip(name):
    require_reader()
    doc = frappe.get_doc('Delivery Trip', name)
    doc.check_permission('read')
    if is_driver() and (doc.docstatus != 1 or doc.driver != driver_for_user()):
        frappe.throw('Chuyến không thuộc tài xế đang đăng nhập.', frappe.PermissionError)
    return doc


@frappe.whitelist()
def list_trips(vehicle=None, active_only=0):
    require_reader()
    filters = {'docstatus': 1}
    if vehicle:
        filters['vehicle'] = vehicle
    if cint(active_only):
        filters['status'] = ['in', ['Scheduled', 'In Transit']]
    if is_driver():
        driver = driver_for_user()
        if not driver:
            return []
        filters['driver'] = driver
    return frappe.get_list('Delivery Trip', filters=filters,
        fields=['name', 'vehicle', 'driver_name', 'status', 'departure_time'],
        order_by='departure_time desc', limit_page_length=500)


def coordinates(stop):
    lat, lng = stop.get('lat'), stop.get('lng')
    # ERPNext uses 0/0 for a stop with no coordinates. Address is an optional fallback.
    if not lat and not lng and stop.get('address'):
        point = frappe.db.get_value('Address', stop.address,
            ['custom_latitude', 'custom_longitude'], as_dict=True)
        if point:
            lat, lng = point.custom_latitude, point.custom_longitude
    if lat is None or lng is None or (not lat and not lng):
        return None, None
    return flt(lat), flt(lng)


@frappe.whitelist()
def get_trip_tracking(delivery_trip):
    doc = readable_trip(delivery_trip)
    from dp_dispatch.completion import get_stop_board
    board = {row['stop']: row for row in get_stop_board(doc.name)}
    stops = []
    for stop in sorted(doc.delivery_stops, key=lambda row: row.idx):
        lat, lng = coordinates(stop)
        row = board[stop.name]
        row.update(name=stop.name, idx=stop.idx, lat=lat, lng=lng,
            confirmations=frappe.get_all('Delivery Confirmation',
                filters={'delivery_trip': doc.name, 'delivery_stop': stop.name, 'docstatus': ['<', 2]},
                fields=['name', 'docstatus'], order_by='creation desc'))
        stops.append(row)
    from dp_dispatch.dp_dispatch.api.gps_redis import latest_for_trip
    return {'trip': {key: doc.get(key) for key in (
        'name', 'vehicle', 'driver', 'driver_name', 'status', 'docstatus',
        'custom_completion_status', 'custom_started_at', 'custom_completed_at',
        'custom_onboard_quantity', 'custom_onboard_weight_kg', 'custom_origin_lat', 'custom_origin_lng')},
        'stops': stops, 'position': latest_for_trip(doc.name, doc.vehicle)}


def gps_log_query(user=None):
    from dp_dispatch.permissions import trip_query
    user = user or frappe.session.user
    if user == 'Administrator' or set(frappe.get_roles(user)) & {'System Manager', 'Fleet Manager'}:
        return ''
    if not is_driver(user):
        return '1=0'
    return '`tabGPS Log`.`delivery_trip` in (select name from `tabDelivery Trip` where ' + trip_query(user) + ')'


def has_gps_log_permission(doc, user=None, permission_type=None, ptype=None):
    permission_type = permission_type or ptype
    user = user or frappe.session.user
    if user == 'Administrator' or set(frappe.get_roles(user)) & {'System Manager', 'Fleet Manager'}:
        return True
    if not is_driver(user) or permission_type not in ('read', 'select', None) or not doc.delivery_trip:
        return False
    from dp_dispatch.permissions import has_trip_permission
    return has_trip_permission(frappe.get_doc('Delivery Trip', doc.delivery_trip), user, 'read')
