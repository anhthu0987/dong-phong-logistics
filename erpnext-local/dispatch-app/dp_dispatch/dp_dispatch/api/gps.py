import frappe
from frappe import _
from frappe.utils import get_datetime

from dp_dispatch.dp_dispatch.api import gps_redis

DRIVER_ROLE = "DP Driver"
SIM_ROLE = "DP GPS Simulator"

# Vai trò điều phối được xem lịch sử GPS (dùng cho trang Fleet Map).
# Muốn CHỈ tài xế tự xem được dữ liệu của mình: đặt DISPATCHER_ROLES = set()
DISPATCHER_ROLES = {"System Manager", "Fleet Manager"}


# ----------------------------------------------------------------------
# Helpers: xác định user là ai, có được phép xem chuyến/xe nào
# ----------------------------------------------------------------------
def _roles():
    return set(frappe.get_roles(frappe.session.user))


def _get_current_driver():
    """Trả về tên Driver liên kết với user đang đăng nhập, hoặc None."""
    from dp_dispatch.permissions import driver_for_user
    return driver_for_user()


def _is_dispatcher():
    return bool(_roles() & DISPATCHER_ROLES)


def _is_simulator():
    return SIM_ROLE in _roles()


def _driver_owns_trip(driver, trip):
    return bool(driver) and frappe.db.get_value("Delivery Trip", trip, "driver") == driver


def _driver_owns_vehicle(driver, vehicle):
    if not driver:
        return False
    return bool(frappe.db.exists(
        "Delivery Trip", {"driver": driver, "vehicle": vehicle, "docstatus": ["<", 2]}
    ))


# ----------------------------------------------------------------------
# GPS ingest (simulator, điều phối, hoặc chính tài xế của xe đó)
# ----------------------------------------------------------------------
@frappe.whitelist(methods=["POST"])
def log_location():
    if frappe.session.user == "Guest":
        frappe.throw(_("Cần đăng nhập hoặc cung cấp API Key để thực hiện"), frappe.PermissionError)

    data = frappe.local.form_dict
    vehicle = data.get("vehicle")
    delivery_trip = data.get("delivery_trip")
    recorded_at = data.get("recorded_at")
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    source_event_id = data.get("source_event_id")
    source_type = data.get("source_type", "Simulated")

    if source_type not in ('Hardware GPS', 'Mobile App', 'Simulated'):
        frappe.throw('Nguồn GPS không hợp lệ.')
    if not vehicle or not recorded_at or latitude is None or longitude is None or not source_event_id:
        frappe.throw(_("Thiếu thông tin bắt buộc trong bản tin GPS"))

    try:
        lat = round(float(latitude), 9)
        lng = round(float(longitude), 9)
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            raise ValueError()
    except ValueError:
        frappe.throw(_("Tọa độ vĩ độ/kinh độ không hợp lệ"))

    if not frappe.db.exists("Vehicle", vehicle):
        frappe.throw(_("Xe {0} không tồn tại").format(vehicle))

    # Tài xế phải gửi theo đúng chuyến được giao, không chỉ theo chiếc xe từng lái.
    if not (_is_simulator() or _is_dispatcher()):
        if not delivery_trip or not _driver_owns_trip(_get_current_driver(), delivery_trip):
            frappe.throw(_("Bạn chỉ được ghi GPS cho chuyến được phân công."), frappe.PermissionError)

    try:
        ts_s = get_datetime(recorded_at).strftime("%Y-%m-%d %H:%M:%S.%f")
    except Exception:
        frappe.throw(_("recorded_at không hợp lệ"))

    if not delivery_trip:
        active = frappe.get_all("Delivery Trip", filters={"vehicle": vehicle, "docstatus": 1, "status": "In Transit"}, pluck="name", limit_page_length=2)
        if len(active) > 1:
            frappe.throw("Xe có nhiều chuyến đang chạy; cần xác định đúng chuyến.")
        delivery_trip = active[0] if active else None
        if delivery_trip:
            started = frappe.db.get_value('Delivery Trip', delivery_trip, 'custom_started_at')
            if not started or get_datetime(ts_s) < get_datetime(started):
                # A delayed vehicle-only message must not be attached to a newer trip.
                delivery_trip = None

    if delivery_trip:
        state = frappe.db.get_value("Delivery Trip", delivery_trip, ["docstatus", "status"], as_dict=True)
        if not state or state.docstatus != 1 or state.status != "In Transit":
            frappe.throw("Chỉ ghi GPS theo chuyến đã bắt đầu và đang thực hiện.")
        trip_vehicle = frappe.db.get_value("Delivery Trip", delivery_trip, "vehicle")
        if trip_vehicle is None:
            frappe.throw(_("Chuyến {0} không tồn tại").format(delivery_trip))
        if trip_vehicle != vehicle:
            frappe.throw(_("Xe {0} không thuộc chuyến {1}").format(vehicle, delivery_trip))

    # Chỉ đẩy vào Redis; flusher (3s) sẽ ghi GPS Log + cập nhật Vehicle.custom_last_*
    point = {
        "vehicle": vehicle,
        "delivery_trip": delivery_trip or None,
        "recorded_at": ts_s,
        "latitude": lat,
        "longitude": lng,
        "source_event_id": source_event_id,
        "source_type": source_type,
    }
    existing = frappe.db.get_value('GPS Log', {'source_event_id': source_event_id},
        ['vehicle', 'delivery_trip', 'recorded_at', 'latitude', 'longitude', 'source_type'], as_dict=True)
    if existing:
        matches = (existing.vehicle == vehicle and (existing.delivery_trip or None) == point['delivery_trip']
            and get_datetime(existing.recorded_at) == get_datetime(ts_s)
            and float(existing.latitude) == lat and float(existing.longitude) == lng
            and existing.source_type == source_type)
        if not matches:
            frappe.throw('source_event_id đã được lưu với dữ liệu khác.', frappe.DuplicateEntryError)
        return {'status': 'ignored', 'source_event_id': source_event_id}
    result = gps_redis.enqueue(point)
    if result == "duplicate":
        return {"status": "ignored", "message": "Bản tin trùng lặp đã được xử lý", "source_event_id": source_event_id}
    return {"status": "success", "queued": True, "source_event_id": source_event_id}


# ----------------------------------------------------------------------
# Lịch sử GPS: chỉ đúng tài xế của xe/chuyến (hoặc điều phối nếu được bật)
# ----------------------------------------------------------------------
@frappe.whitelist(methods=["GET", "POST"])
def get_gps_history(vehicle=None, delivery_trip=None, limit=100):
    if frappe.session.user == "Guest":
        frappe.throw(_("Cần đăng nhập"), frappe.PermissionError)

    if not vehicle and not delivery_trip:
        frappe.throw(_("Cần cung cấp vehicle hoặc delivery_trip"))

    from dp_dispatch.tracking import require_reader, readable_trip
    from dp_dispatch.permissions import is_driver
    require_reader()
    if delivery_trip:
        doc = readable_trip(delivery_trip)
        if vehicle and doc.vehicle != vehicle:
            frappe.throw("Xe không thuộc chuyến đã chọn.")
    driver = _get_current_driver() if is_driver() else None
    if is_driver() and not driver:
        frappe.throw("Tài khoản chưa liên kết tài xế.", frappe.PermissionError)

    conditions = []
    values = {}

    if driver:
        conditions.append("delivery_trip IN (SELECT name FROM `tabDelivery Trip` WHERE driver = %(driver)s)")
        values["driver"] = driver

    if vehicle:
        conditions.append("vehicle = %(vehicle)s")
        values["vehicle"] = vehicle
    if delivery_trip:
        conditions.append("delivery_trip = %(delivery_trip)s")
        values["delivery_trip"] = delivery_trip

    where_clause = " AND ".join(conditions)
    values["limit"] = max(1, min(int(limit), 3000))

    query = f"""
        SELECT recorded_at, latitude, longitude, source_type, source_event_id
        FROM `tabGPS Log`
        WHERE {where_clause}
        ORDER BY recorded_at DESC, name DESC
        LIMIT %(limit)s
    """

    return list(reversed(frappe.db.sql(query, values, as_dict=True)))


# ----------------------------------------------------------------------
# Trang tài xế: chỉ chính tài xế mới xem/thao tác được chuyến của mình
# ----------------------------------------------------------------------
@frappe.whitelist(methods=["GET", "POST"])
def get_driver_schedule(delivery_trip=None):
    from dp_dispatch.tracking import list_trips, get_trip_tracking
    trips = list_trips(active_only=1)
    if not delivery_trip:
        active = [t for t in trips if t.status == 'In Transit']
        delivery_trip = (active or list(reversed(trips)))[0].name if trips else None
    result = get_trip_tracking(delivery_trip) if delivery_trip else {'trip': None, 'stops': []}
    result['trips'] = trips
    return result


@frappe.whitelist(methods=["POST"])
def complete_delivery_stop(stop_name=None):
    # Retired endpoint: old browser tabs must never bypass confirmation/approval.
    frappe.throw("Hãy tải lại trang và dùng Ghi nhận lấy/giao để lập phiếu Delivery Confirmation. GPS không hoàn tất chuyến.")
