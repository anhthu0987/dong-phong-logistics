import frappe
from frappe import _
from frappe.utils import get_datetime

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
    user = frappe.session.user
    if user in ("Administrator", "Guest"):
        return None

    meta = frappe.get_meta("Driver")
    for field in ("custom_user", "user"):
        if meta.has_field(field):
            name = frappe.db.get_value("Driver", {field: user}, "name")
            if name:
                return name

    # Fallback: Driver -> Employee -> User
    if meta.has_field("employee"):
        emp = frappe.db.get_value("Employee", {"user_id": user}, "name")
        if emp:
            return frappe.db.get_value("Driver", {"employee": emp}, "name")
    return None


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

    if not vehicle or not recorded_at or latitude is None or longitude is None or not source_event_id:
        frappe.throw(_("Thiếu thông tin bắt buộc trong bản tin GPS"))

    try:
        lat = float(latitude)
        lng = float(longitude)
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

    if delivery_trip:
        if not frappe.db.exists("Delivery Trip", delivery_trip):
            frappe.throw(_("Chuyến {0} không tồn tại").format(delivery_trip))
        trip_doc = frappe.get_doc("Delivery Trip", delivery_trip)
        if trip_doc.vehicle != vehicle:
            frappe.throw(_("Xe {0} không thuộc chuyến {1}").format(vehicle, delivery_trip))

    existing = frappe.db.get_value(
        "GPS Log", {"source_event_id": source_event_id}, ["name", "latitude", "longitude"], as_dict=True
    )
    if existing:
        if float(existing.latitude) == lat and float(existing.longitude) == lng:
            return {"status": "ignored", "message": "Bản tin trùng lặp đã được xử lý", "source_event_id": source_event_id}
        else:
            frappe.throw(
                _("Xung đột: source_event_id {0} đã tồn tại với nội dung khác").format(source_event_id),
                frappe.DuplicateEntryError,
            )

    gps_doc = frappe.get_doc({
        "doctype": "GPS Log",
        "vehicle": vehicle,
        "delivery_trip": delivery_trip,
        "recorded_at": recorded_at,
        "latitude": lat,
        "longitude": lng,
        "source_event_id": source_event_id,
        "source_type": source_type,
    })
    gps_doc.insert(ignore_permissions=True)

    current_last_time = frappe.db.get_value("Vehicle", vehicle, "custom_last_gps_time")
    new_time = get_datetime(recorded_at)

    if not current_last_time or new_time >= get_datetime(current_last_time):
        frappe.db.set_value("Vehicle", vehicle, {
            "custom_last_lat": lat,
            "custom_last_lng": lng,
            "custom_last_gps_time": recorded_at,
        }, update_modified=False)

    frappe.db.commit()
    return {"status": "success", "source_event_id": source_event_id, "name": gps_doc.name}


# ----------------------------------------------------------------------
# Lịch sử GPS: chỉ đúng tài xế của xe/chuyến (hoặc điều phối nếu được bật)
# ----------------------------------------------------------------------
@frappe.whitelist(methods=["GET", "POST"])
def get_gps_history(vehicle=None, delivery_trip=None, limit=100):
    if frappe.session.user == "Guest":
        frappe.throw(_("Cần đăng nhập"), frappe.PermissionError)

    if not vehicle and not delivery_trip:
        frappe.throw(_("Cần cung cấp vehicle hoặc delivery_trip"))

    driver = None
    if not _is_dispatcher():
        driver = _get_current_driver()
        if not driver:
            frappe.throw(_("Bạn không có quyền xem dữ liệu GPS"), frappe.PermissionError)
        if vehicle and not _driver_owns_vehicle(driver, vehicle):
            frappe.throw(_("Bạn không có quyền xem GPS của xe {0}").format(vehicle), frappe.PermissionError)
        if delivery_trip and not _driver_owns_trip(driver, delivery_trip):
            frappe.throw(_("Chuyến {0} không thuộc về bạn").format(delivery_trip), frappe.PermissionError)

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
    values["limit"] = int(limit)

    query = f"""
        SELECT recorded_at, latitude, longitude, source_type, source_event_id
        FROM `tabGPS Log`
        WHERE {where_clause}
        ORDER BY recorded_at ASC
        LIMIT %(limit)s
    """

    return frappe.db.sql(query, values, as_dict=True)


# ----------------------------------------------------------------------
# Trang tài xế: chỉ chính tài xế mới xem/thao tác được chuyến của mình
# ----------------------------------------------------------------------
@frappe.whitelist(methods=["GET", "POST"])
def get_driver_schedule():
    if frappe.session.user == "Guest":
        frappe.throw(_("Cần đăng nhập để xem lịch trình"), frappe.PermissionError)

    driver = _get_current_driver()
    
    # Strictly enforce driver identity and role check
    if not driver or DRIVER_ROLE not in _roles():
        return {"trip": None, "stops": []}

    # Removed ignore_permissions=True to respect User Permissions
    trips = frappe.get_all(
        "Delivery Trip",
        filters={
            "driver": driver,
            "docstatus": ["<", 2],
            "status": ["not in", ["Completed", "Cancelled"]],
        },
        fields=["name", "vehicle", "driver_name", "status"],
        order_by="departure_time desc",
        limit_page_length=1
    )

    if not trips:
        return {"trip": None, "stops": []}

    trip = trips[0]
    stops = frappe.get_all(
        "Delivery Stop",
        filters={"parent": trip["name"], "parenttype": "Delivery Trip"},
        fields=["name", "idx", "customer", "address", "lat", "lng", "visited"],
        order_by="idx asc",
        limit_page_length=100
    )

    return {"trip": trip, "stops": stops}


@frappe.whitelist(methods=["POST"])
def complete_delivery_stop(stop_name=None):
    if frappe.session.user == "Guest":
        frappe.throw(_("Cần đăng nhập để thực hiện thao tác này"), frappe.PermissionError)

    if not stop_name:
        stop_name = frappe.local.form_dict.get("stop_name")

    if not stop_name or not frappe.db.exists("Delivery Stop", stop_name):
        frappe.throw(_("Không tìm thấy điểm dừng hợp lệ"))

    parent_trip = frappe.db.get_value("Delivery Stop", stop_name, "parent")

    # Giữ khóa chuyến đến khi cập nhật xong, tránh xác nhận đồng thời với thao tác hủy.
    trip = frappe.db.get_value(
        "Delivery Trip", parent_trip, ["driver", "docstatus", "status"],
        as_dict=True, for_update=True,
    )

    # Chỉ đúng tài xế của chuyến này mới được đánh dấu (không có ngoại lệ, kể cả quản trị)
    driver = _get_current_driver()
    if not trip or not driver or trip.driver != driver:
        frappe.throw(_("Điểm dừng này không thuộc chuyến của bạn"), frappe.PermissionError)

    if trip.docstatus == 2 or trip.status == "Cancelled":
        frappe.throw(_("Không thể xác nhận điểm giao của chuyến đã hủy."))

    frappe.db.set_value("Delivery Stop", stop_name, "visited", 1, update_modified=True)

    unvisited_count = frappe.db.count("Delivery Stop", filters={"parent": parent_trip, "visited": 0})

    trip_completed = False
    if unvisited_count == 0:
        frappe.db.set_value("Delivery Trip", parent_trip, "status", "Completed", update_modified=True)
        trip_completed = True

    frappe.db.commit()
    return {"status": "success", "stop_name": stop_name, "trip_completed": trip_completed}
