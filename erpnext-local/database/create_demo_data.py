import frappe

def create_defaults():
    frappe.set_user("Administrator")

    # 1. Ensure Company exists
    company_name = "Đông Phong"
    if not frappe.db.exists("Company", company_name):
        frappe.get_doc({
            "doctype": "Company",
            "company_name": company_name,
            "default_currency": "VND",
            "country": "Vietnam"
        }).insert(ignore_permissions=True)
        print(f"  [+] Created Company: {company_name}")

    # 2. Ensure Driver exists
    driver_id = "DRI-DP-001"
    if not frappe.db.exists("Driver", driver_id):
        frappe.get_doc({
            "doctype": "Driver",
            "name": driver_id,
            "full_name": "Tài xế Đông Phong",
            "status": "Active"
        }).insert(ignore_permissions=True)
        print(f"  [+] Created Driver: {driver_id}")

    # 3. Create active Delivery Trip for vehicle 51C-123.45
    vehicle_plate = "51C-123.45"
    if not frappe.db.exists("Delivery Trip", {"vehicle": vehicle_plate, "docstatus": ["<", 2]}):
        trip = frappe.get_doc({
            "doctype": "Delivery Trip",
            "company": company_name,
            "vehicle": vehicle_plate,
            "driver": driver_id,
            "departure_time": frappe.utils.now_datetime(),
            "custom_expected_end_time": frappe.utils.add_to_date(frappe.utils.now_datetime(), hours=4),
            "custom_planned_load_kg": 1000,
            "status": "Scheduled",
            "delivery_stops": [
                {"customer": "Khách hàng A", "address": "Sài Gòn", "lat": 10.7769, "lng": 106.7009},
                {"customer": "Khách hàng B", "address": "Biên Hòa", "lat": 10.9575, "lng": 106.8427}
            ]
        })
        trip.insert(ignore_permissions=True)
        print(f"  [+] Created Delivery Trip for vehicle: {vehicle_plate}")

    frappe.db.commit()
    print("✅ Master Data & Delivery Trip Created Successfully!")

if __name__ == "__main__":
    create_defaults()
