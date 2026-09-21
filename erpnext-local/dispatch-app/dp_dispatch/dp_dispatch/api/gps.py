import frappe
from frappe import _
from frappe.utils import get_datetime

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

    if delivery_trip:
        if not frappe.db.exists("Delivery Trip", delivery_trip):
            frappe.throw(_("Chuyến {0} không tồn tại").format(delivery_trip))
        trip_doc = frappe.get_doc("Delivery Trip", delivery_trip)
        if trip_doc.vehicle != vehicle:
            frappe.throw(_("Xe {0} không thuộc chuyến {1}").format(vehicle, delivery_trip))

    existing = frappe.db.get_value("GPS Log", {"source_event_id": source_event_id}, ["name", "latitude", "longitude"], as_dict=True)
    if existing:
        if float(existing.latitude) == lat and float(existing.longitude) == lng:
            return {"status": "ignored", "message": "Bản tin trùng lặp đã được xử lý", "source_event_id": source_event_id}
        else:
            frappe.throw(_("Xung đột: source_event_id {0} đã tồn tại với nội dung khác").format(source_event_id), frappe.DuplicateEntryError)

    gps_doc = frappe.get_doc({
        "doctype": "GPS Log",
        "vehicle": vehicle,
        "delivery_trip": delivery_trip,
        "recorded_at": recorded_at,
        "latitude": lat,
        "longitude": lng,
        "source_event_id": source_event_id,
        "source_type": source_type
    })
    gps_doc.insert(ignore_permissions=True)

    current_last_time = frappe.db.get_value("Vehicle", vehicle, "custom_last_gps_time")
    new_time = get_datetime(recorded_at)
    
    if not current_last_time or new_time >= get_datetime(current_last_time):
        frappe.db.set_value("Vehicle", vehicle, {
            "custom_last_lat": lat,
            "custom_last_lng": lng,
            "custom_last_gps_time": recorded_at
        }, update_modified=False)

    frappe.db.commit()
    return {"status": "success", "source_event_id": source_event_id, "name": gps_doc.name}


@frappe.whitelist(methods=["GET", "POST"])
def get_gps_history(vehicle=None, delivery_trip=None, limit=100):
    if not vehicle and not delivery_trip:
        frappe.throw(_("Cần cung cấp vehicle hoặc delivery_trip"))

    conditions = []
    values = {}

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

    logs = frappe.db.sql(query, values, as_dict=True)
    return logs


@frappe.whitelist(methods=["GET", "POST"])
def get_driver_schedule():
    if frappe.session.user == "Guest":
        frappe.throw(_("Cần đăng nhập để xem lịch trình"), frappe.PermissionError)

    trips = frappe.get_all(
        "Delivery Trip",
        filters={"docstatus": ["<", 2]},
        fields=["name", "vehicle", "driver_name", "status"],
        order_by="creation desc",
        limit_page_length=1,
        ignore_permissions=True
    )

    if not trips:
        return {"trip": None, "stops": []}

    trip = trips[0]
    stops = frappe.get_all(
        "Delivery Stop",
        filters={"parent": trip["name"]},
        fields=["name", "idx", "customer", "address", "lat", "lng", "visited"],
        order_by="idx asc",
        limit_page_length=100,
        ignore_permissions=True
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

    frappe.db.set_value("Delivery Stop", stop_name, "visited", 1, update_modified=True)
    
    parent_trip = frappe.db.get_value("Delivery Stop", stop_name, "parent")
    unvisited_count = frappe.db.count("Delivery Stop", filters={"parent": parent_trip, "visited": 0})
    
    trip_completed = False
    if unvisited_count == 0:
        frappe.db.set_value("Delivery Trip", parent_trip, "status", "Completed", update_modified=True)
        trip_completed = True

    frappe.db.commit()
    return {"status": "success", "stop_name": stop_name, "trip_completed": trip_completed}
