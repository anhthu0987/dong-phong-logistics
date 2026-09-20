app_name = "dp_operations"
app_title = "Dong Phong Operations"
app_publisher = "Dong Phong Project"
app_description = "Delivery confirmation, fuel/service logging, maintenance for the midterm simulation"
app_email = "project@example.invalid"
app_license = "MIT"
required_apps = ["erpnext"]

after_install = "dp_operations.setup.install"
after_migrate = "dp_operations.setup.install"

doc_events = {
    "Vehicle Log": {
        "validate": "dp_operations.validation.validate_vehicle_log",
        "before_submit": "dp_operations.validation.validate_vehicle_log",
    }
}
