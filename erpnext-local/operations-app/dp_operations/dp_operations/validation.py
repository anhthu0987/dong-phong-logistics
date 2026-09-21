import frappe

def validate_vehicle_log(doc, method=None):
    if doc.get("custom_delivery_trip"):
        trip_vehicle = frappe.db.get_value("Delivery Trip", doc.custom_delivery_trip, "vehicle")
        if trip_vehicle and trip_vehicle != doc.license_plate:
            frappe.throw(
                f"Xe trong Vehicle Log ({doc.license_plate}) phải trùng với xe của chuyến đã chọn ({trip_vehicle}).",
                title="DP_VEHICLE_MISMATCH"
            )
