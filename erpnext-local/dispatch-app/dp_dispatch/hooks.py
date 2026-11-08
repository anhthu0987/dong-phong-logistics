app_name = 'dp_dispatch'
app_title = 'Dong Phong Dispatch'
app_publisher = 'Dong Phong Project'
app_description = 'Delivery orders, dispatch, driver operations, and fleet management'
app_email = 'project@example.invalid'
app_license = 'MIT'
required_apps = ['erpnext']

after_install = 'dp_dispatch.setup.install'
after_migrate = 'dp_dispatch.setup.install'

doctype_js = {
    'Delivery Trip': 'public/js/delivery_trip.js',
    'Delivery Order': 'public/js/delivery_order.js',
    'Delivery Confirmation': 'public/js/delivery_confirmation.js',
    'Fleet Maintenance Record': 'public/js/fleet_maintenance_record.js',
}

permission_query_conditions = {
	'Vehicle Log': 'dp_dispatch.permissions.vehicle_log_query',
	'Vehicle': 'dp_dispatch.permissions.vehicle_query',
    'Delivery Trip': 'dp_dispatch.permissions.trip_query',
    'Delivery Confirmation': 'dp_dispatch.permissions.confirmation_query',
    'Delivery Order': 'dp_dispatch.permissions.delivery_order_query',
}
has_permission = {
	'Vehicle Log': 'dp_dispatch.permissions.has_vehicle_log_permission',
	'Vehicle': 'dp_dispatch.permissions.has_vehicle_permission',
    'Delivery Trip': 'dp_dispatch.permissions.has_trip_permission',
    'Delivery Confirmation': 'dp_dispatch.permissions.has_confirmation_permission',
    'Delivery Order': 'dp_dispatch.permissions.has_delivery_order_permission',
}

doc_events = {
	'Quotation': {
		'validate': 'dp_dispatch.sales.prevent_unaccepting_quotation_with_order',
	},
	'Delivery Order': {
        'validate': 'dp_dispatch.transport.validate_order',
        'before_cancel': 'dp_dispatch.transport.before_cancel_order',
        'on_submit': 'dp_dispatch.delivery_confirmation.on_submit_order',
    },
    'Delivery Trip': {
        'before_cancel': 'dp_dispatch.transport.before_cancel_trip',
        'on_cancel': 'dp_dispatch.transport.on_cancel_trip',
        'validate': 'dp_dispatch.validation.validate_trip',
        'before_submit': 'dp_dispatch.validation.validate_trip',
        'before_update_after_submit': 'dp_dispatch.validation.validate_odometer',
    },
    'Vehicle': {'validate': 'dp_dispatch.validation.validate_vehicle'},
    'Vehicle Log': {
        'validate': 'dp_dispatch.maintenance.validate_vehicle_log',
        'before_submit': 'dp_dispatch.maintenance.validate_vehicle_log',
    },
    'Delivery Confirmation': {
        'validate': 'dp_dispatch.delivery_confirmation.validate_confirmation',
        'before_submit': 'dp_dispatch.delivery_confirmation.validate_confirmation',
        'on_submit': 'dp_dispatch.delivery_confirmation.on_submit_confirmation',
        'on_cancel': 'dp_dispatch.delivery_confirmation.on_cancel_confirmation',
        'before_cancel': 'dp_dispatch.delivery_confirmation.before_cancel_confirmation',
    },
    'Fleet Maintenance Plan': {
        'validate': 'dp_dispatch.maintenance.validate_plan',
        'on_update': 'dp_dispatch.maintenance.sync_plan_vehicle_status',
    },
    'Fleet Maintenance Record': {
        'validate': 'dp_dispatch.maintenance.validate_record',
        'before_submit': 'dp_dispatch.maintenance.validate_record',
        'on_submit': 'dp_dispatch.maintenance.accept_record',
    },
}
