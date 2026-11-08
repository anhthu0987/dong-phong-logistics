import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.permissions import add_permission, update_permission_property

COORD = dict(fieldtype='Float', precision='9')

CUSTOM_FIELDS = {
    'Vehicle': [
        dict(fieldname='custom_payload_capacity_kg', label='Payload Capacity (kg)', fieldtype='Float',
             non_negative=1, insert_after='model'),
        dict(fieldname='custom_technical_status', label='Technical Status', fieldtype='Select',
             options='Available\nUnder Maintenance\nOut of Service', default='Available',
             insert_after='custom_payload_capacity_kg'),
        dict(fieldname='custom_gps_device_id', label='GPS Device ID', fieldtype='Data',
             search_index=1, insert_after='custom_technical_status'),
        dict(fieldname='custom_last_lat', label='Last GPS Latitude', insert_after='custom_gps_device_id',
             read_only=1, **COORD),
        dict(fieldname='custom_last_lng', label='Last GPS Longitude', insert_after='custom_last_lat',
             read_only=1, **COORD),
        dict(fieldname='custom_last_gps_time', label='Last GPS Time', fieldtype='Datetime',
             read_only=1, insert_after='custom_last_lng'),
    ],
    'Address': [
        dict(fieldname='custom_latitude', label='Latitude', insert_after='pincode', **COORD),
        dict(fieldname='custom_longitude', label='Longitude', insert_after='custom_latitude', **COORD),
        dict(fieldname='custom_geocode_source', label='Geocode Source', fieldtype='Select',
             options='Manual\nGoogle Maps\nOpenStreetMap\nGPS Device', default='Manual',
             insert_after='custom_longitude'),
    ],
    'Delivery Trip': [
        dict(fieldname='custom_expected_end_time', label='Expected End Time', fieldtype='Datetime',
             insert_after='departure_time'),
        dict(fieldname='custom_start_odometer', label='Start Odometer (km)', fieldtype='Int',
             non_negative=1, insert_after='custom_expected_end_time'),
        dict(fieldname='custom_end_odometer', label='End Odometer (km)', fieldtype='Int',
             non_negative=1, insert_after='custom_start_odometer'),
        dict(fieldname='custom_planned_load_kg', label='Planned Load (kg)', fieldtype='Float',
             non_negative=1, insert_after='custom_end_odometer'),
        dict(fieldname='custom_origin_lat', label='Origin Latitude', insert_after='custom_planned_load_kg',
             **COORD),
        dict(fieldname='custom_origin_lng', label='Origin Longitude', insert_after='custom_origin_lat',
             **COORD),
    ],
}

def setup_roles_and_pages():
    for r_name in ["GPS Device", "Driver", "Fleet Manager"]:
        if not frappe.db.exists("Role", r_name):
            frappe.get_doc({"doctype": "Role", "role_name": r_name, "desk_access": 1}).insert(ignore_permissions=True)

    pages = [
        {"page_name": "fleet-map", "title": "Fleet map"},
        {"page_name": "driver-gps", "title": "Lịch trình Tài xế"}
    ]
    for p in pages:
        if not frappe.db.exists("Page", p["page_name"]):
            page_doc = frappe.get_doc({
                "doctype": "Page",
                "page_name": p["page_name"],
                "title": p["title"],
                "module": "Dp Dispatch",
                "standard": "Yes",
                "roles": [
                    {"role": "System Manager"},
                    {"role": "Fleet Manager"},
                    {"role": "Driver"},
                    {"role": "Administrator"}
                ]
            })
            page_doc.insert(ignore_permissions=True)

def setup_gps_log_doctype():
    doctype_name = "GPS Log"
    if not frappe.db.exists("DocType", doctype_name):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "name": doctype_name,
            "module": "Dp Dispatch",
            "custom": 1,
            "is_submittable": 0,
            "track_changes": 0,
            "autoname": "hash",
            "fields": [
                {"fieldname": "vehicle", "label": "Vehicle", "fieldtype": "Link", "options": "Vehicle", "reqd": 1, "in_list_view": 1, "search_index": 1},
                {"fieldname": "delivery_trip", "label": "Delivery Trip", "fieldtype": "Link", "options": "Delivery Trip", "in_list_view": 1, "search_index": 1},
                {"fieldname": "recorded_at", "label": "Recorded At", "fieldtype": "Datetime", "reqd": 1, "in_list_view": 1, "search_index": 1},
                {"fieldname": "latitude", "label": "Latitude", "fieldtype": "Float", "precision": "9", "reqd": 1, "in_list_view": 1},
                {"fieldname": "longitude", "label": "Longitude", "fieldtype": "Float", "precision": "9", "reqd": 1, "in_list_view": 1},
                {"fieldname": "source_event_id", "label": "Source Event ID", "fieldtype": "Data", "reqd": 1, "unique": 1, "in_list_view": 1},
                {"fieldname": "source_type", "label": "Source Type", "fieldtype": "Select", "options": "Hardware GPS\nMobile App\nSimulated", "default": "Simulated", "reqd": 1, "in_list_view": 1}
            ],
            "permissions": [
                {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1},
                {"role": "Fleet Manager", "read": 1, "write": 1, "create": 1, "delete": 0},
                {"role": "GPS Device", "read": 1, "write": 0, "create": 1, "delete": 0},
                {"role": "Driver", "read": 1, "write": 0, "create": 0, "delete": 0},
                {"role": "All", "read": 1, "write": 0, "create": 0, "delete": 0}
            ]
        })
        doc.insert(ignore_permissions=True)

    index_queries = [
        "ALTER TABLE `tabGPS Log` ADD INDEX `idx_vehicle_recorded` (`vehicle`, `recorded_at`);",
        "ALTER TABLE `tabGPS Log` ADD INDEX `idx_trip_recorded` (`delivery_trip`, `recorded_at`);"
    ]
    for q in index_queries:
        try:
            frappe.db.sql(q)
        except Exception:
            pass

def setup_database():
    print("==================================================")
    print("🚀 THIẾT LẬP DATABASE SCHEMA SNAPSHOT V5 (NO SEED DATA)")
    print("==================================================")

    create_custom_fields(CUSTOM_FIELDS, update=False)
    if not frappe.get_meta('Vehicle').allow_import:
        make_property_setter('Vehicle', None, 'allow_import', 1, 'Check', for_doctype=True)
    update_permission_property('Vehicle', 'Fleet Manager', 0, 'import', 1)
    print(">>> [1/4] Đã đồng bộ Custom Fields (Precision 9 cho Tọa độ)")

    setup_roles_and_pages()
    print(">>> [2/4] Đã đăng ký Roles & Pages 'fleet-map' / 'driver-gps'")

    setup_gps_log_doctype()
    print(">>> [3/4] Đã thiết lập DocType 'GPS Log' & Database Indexes")

    target_roles = ["Driver", "Fleet Manager", "GPS Device"]
    target_doctypes = ["Delivery Trip", "Delivery Stop", "Vehicle"]

    for dt in target_doctypes:
        for r in target_roles:
            add_permission(dt, r, ptype=0)
            add_permission(dt, r, ptype=1)
            if r == "Fleet Manager":
                add_permission(dt, r, ptype=2)
    print(">>> [4/4] Đã cấp quyền DocPerm chuẩn cho Delivery Trip, Delivery Stop & Vehicle")

    frappe.clear_cache()
    frappe.db.commit()
    print("==================================================")
    print("🎉 HOÀN TẤT THIẾT LẬP SYSTEM SCHEMA SNAPSHOT V5!")
    print("==================================================")

if __name__ == "__main__":
    setup_database()
