import frappe, json

def fix():
    frappe.set_user("Administrator")
    
    # Clean up SQL direct records
    frappe.db.sql("SET SQL_SAFE_UPDATES = 0;")
    frappe.db.sql("TRUNCATE TABLE `tabInstalled Application`")
    
    apps = ["frappe", "erpnext", "hrms", "dp_dispatch"]
    for idx, app in enumerate(apps, 1):
        frappe.db.sql("""
            INSERT INTO `tabInstalled Application` 
            (name, creation, modified, modified_by, owner, docstatus, idx, parent, parentfield, parenttype, app_name, app_version) 
            VALUES (%s, NOW(), NOW(), 'Administrator', 'Administrator', 0, %s, 'Installed Applications', 'installed_applications', 'Installed Applications', %s, '15.0.0')
        """, (frappe.generate_hash(length=10), idx, app))
    
    frappe.db.set_global("installed_apps", json.dumps(apps))
    frappe.db.commit()
    print("✅ Successfully repaired Installed Applications table structure!")

if __name__ == "__main__":
    fix()
