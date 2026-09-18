app_name = 'dp_dispatch'
app_title = 'Dong Phong Dispatch'
app_publisher = 'Dong Phong Project'
app_description = 'Fleet and driver scheduling for the midterm simulation'
app_email = 'project@example.invalid'
app_license = 'MIT'
required_apps = ['erpnext']
after_install = 'dp_dispatch.setup.install'
after_migrate = 'dp_dispatch.setup.install'
doc_events = {
    'Delivery Trip': {
        'validate': 'dp_dispatch.validation.validate_trip',
        'before_submit': 'dp_dispatch.validation.validate_trip',
        'before_update_after_submit': 'dp_dispatch.validation.validate_odometer',
    },
    'Vehicle': {'validate': 'dp_dispatch.validation.validate_vehicle'},
}
