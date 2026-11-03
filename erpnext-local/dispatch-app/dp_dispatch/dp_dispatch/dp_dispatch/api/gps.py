import json
import frappe
from frappe import _
from frappe.utils import now_datetime

REDIS_FLEET_KEY = "fleet_live_locations"
REDIS_BUFFER_KEY = "gps_log_buffer"

@frappe.whitelist(methods=["POST"])
def log_location():
    if frappe.session.user == "Guest":
        frappe.throw(_("Requires Authentication"), frappe.PermissionError)

    data = frappe.local.form_dict
    vehicle = data.get("vehicle")
    delivery_trip = data.get("delivery_trip")
    recorded_at = data.get("recorded_at") or str(now_datetime())
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    source_event_id = data.get("source_event_id")
    source_type = data.get("source_type", "Simulated")

    if not vehicle or latitude is None or longitude is None or not source_event_id:
        frappe.throw(_("Missing required parameters"))

    lat, lng = float(latitude), float(longitude)
    payload = {
        "vehicle": vehicle,
        "delivery_trip": delivery_trip,
        "recorded_at": str(recorded_at),
        "latitude": lat,
        "longitude": lng,
        "source_event_id": source_event_id,
        "source_type": source_type
    }

    cache = frappe.cache()
    cache.hset(REDIS_FLEET_KEY, vehicle, json.dumps(payload))
    cache.rpush(REDIS_BUFFER_KEY, json.dumps(payload))

    frappe.db.set_value("Vehicle", vehicle, {
        "custom_last_lat": lat,
        "custom_last_lng": lng,
        "custom_last_gps_time": recorded_at
    }, update_modified=False)

    return {"status": "success", "storage": "redis"}

@frappe.whitelist(methods=["GET", "POST"])
def get_fleet_live_locations():
    cache = frappe.cache()
    raw_data = cache.hgetall(REDIS_FLEET_KEY) or {}
    fleet_locations = []
    for vehicle, payload_str in raw_data.items():
        try:
            if isinstance(payload_str, bytes):
                payload_str = payload_str.decode("utf-8")
            fleet_locations.append(json.loads(payload_str))
        except Exception:
            continue
    return fleet_locations

def flush_gps_buffer_to_db():
    cache = frappe.cache()
    logs_to_insert = []
    for _ in range(500):
        item = cache.lpop(REDIS_BUFFER_KEY)
        if not item:
            break
        if isinstance(item, bytes):
            item = item.decode("utf-8")
        logs_to_insert.append(json.loads(item))

    if not logs_to_insert:
        return

    for log in logs_to_insert:
        if frappe.db.exists("GPS Log", {"source_event_id": log["source_event_id"]}):
            continue
        doc = frappe.get_doc({
            "doctype": "GPS Log",
            "vehicle": log["vehicle"],
            "delivery_trip": log.get("delivery_trip"),
            "recorded_at": log["recorded_at"],
            "latitude": log["latitude"],
            "longitude": log["longitude"],
            "source_event_id": log["source_event_id"],
            "source_type": log.get("source_type", "Simulated")
        })
        doc.insert(ignore_permissions=True)

    frappe.db.commit()
    print(f"✅ Flushed {len(logs_to_insert)} items to DB")
