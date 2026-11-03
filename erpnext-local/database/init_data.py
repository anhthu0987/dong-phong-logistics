import frappe

def initialize_dong_phong_defaults():
    """
    Automates prerequisite master data initialization for Dong Phong Logistics.
    Safe to run multiple times (idempotent).
    """
    frappe.set_user("Administrator")
    print("🚀 Starting Dong Phong Logistics Data Initialization...")

    # 1. Ensure UOM "Litre" exists
    if not frappe.db.exists("UOM", "Litre"):
        uom = frappe.get_doc({
            "doctype": "UOM",
            "uom_name": "Litre",
            "must_be_whole_number": 0
        })
        uom.insert(ignore_permissions=True)
        print("  [+] Created UOM: Litre")
    else:
        print("  [=] UOM Litre already exists")

    # 2. Ensure Customer Group "Commercial" exists
    if not frappe.db.exists("Customer Group", "Commercial"):
        cg = frappe.get_doc({
            "doctype": "Customer Group",
            "customer_group_name": "Commercial",
            "is_group": 0
        })
        cg.insert(ignore_permissions=True)
        print("  [+] Created Customer Group: Commercial")
    else:
        print("  [=] Customer Group Commercial already exists")

    # 3. Ensure Territory "Vietnam" exists
    if not frappe.db.exists("Territory", "Vietnam"):
        ter = frappe.get_doc({
            "doctype": "Territory",
            "territory_name": "Vietnam",
            "is_group": 0
        })
        ter.insert(ignore_permissions=True)
        print("  [+] Created Territory: Vietnam")
    else:
        print("  [=] Territory Vietnam already exists")

    # 4. Create or Update Vehicle 51C-123.45
    vehicle_license = "51C-123.45"
    if not frappe.db.exists("Vehicle", vehicle_license):
        vehicle = frappe.get_doc({
            "doctype": "Vehicle",
            "license_plate": vehicle_license,
            "make": "Dong Phong Demo",
            "model": "Truck 2026",
            "payload_capacity": 2000,
            "custom_technical_status": "Available" if frappe.db.has_column("Vehicle", "custom_technical_status") else None
        })
        vehicle.insert(ignore_permissions=True)
        print(f"  [+] Created Vehicle: {vehicle_license} (Payload: 2000kg)")
    else:
        vehicle = frappe.get_doc("Vehicle", vehicle_license)
        vehicle.payload_capacity = 2000
        if hasattr(vehicle, "custom_technical_status"):
            vehicle.custom_technical_status = "Available"
        vehicle.save(ignore_permissions=True)
        print(f"  [^] Updated Vehicle: {vehicle_license} (Payload set to 2000kg)")

    frappe.db.commit()
    print("✅ Dong Phong Logistics Initialization Completed Successfully!")


if __name__ == "__main__":
    initialize_dong_phong_defaults()