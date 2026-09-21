import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def install():
    create_custom_fields({
        'Vehicle Log': [
            dict(
                fieldname='custom_delivery_trip',
                label='Delivery Trip',
                fieldtype='Link',
                options='Delivery Trip',
                insert_after='odometer',
                description='Gắn chi phí nhiên liệu/dịch vụ với chuyến (tuỳ chọn).'
            ),
        ],
    }, update=True)
    frappe.clear_cache()
