import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def install():
    create_custom_fields({
        'Vehicle':[
            dict(fieldname='custom_payload_capacity_kg',label='Payload Capacity (kg)',fieldtype='Float',non_negative=1,insert_after='model',description='Simulation capacity must be set before submitting a trip.'),
            dict(fieldname='custom_technical_status',label='Technical Status',fieldtype='Select',options='Available\nUnder Maintenance\nOut of Service',default='Available',insert_after='custom_payload_capacity_kg'),
        ],
        'Delivery Trip':[
            dict(fieldname='custom_expected_end_time',label='Expected End Time',fieldtype='Datetime',insert_after='departure_time',description='Required to submit. Adjacent trips may share the same end/start time.'),
            dict(fieldname='custom_start_odometer',label='Start Odometer (km)',fieldtype='Int',non_negative=1,insert_after='custom_expected_end_time'),
            dict(fieldname='custom_end_odometer',label='End Odometer (km)',fieldtype='Int',non_negative=1,allow_on_submit=1,insert_after='custom_start_odometer',description='Leave at 0 until the end reading is known; otherwise must be >= start reading.'),
            dict(fieldname='custom_planned_load_kg',label='Planned Load (kg)',fieldtype='Float',non_negative=1,insert_after='custom_end_odometer',description='Manually declared load for simulation, not automatically calculated from Delivery Notes. Must be > 0 to submit.'),
        ],
    },update=True)
    frappe.db.add_index('Delivery Trip',['vehicle','departure_time'],'dp_vehicle_departure')
    frappe.db.add_index('Delivery Trip',['driver','departure_time'],'dp_driver_departure')
    frappe.clear_cache()
