"""Idempotent schema for transport/accounting links; no automatic GL posting."""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def install():
    def link(name, label, target):
        return dict(fieldname=name, label=label, fieldtype='Link', options=target, read_only=1, no_copy=1)
    create_custom_fields({
        'Delivery Order': [
            dict(fieldname='custom_payment_policy', label='Điều kiện thanh toán cước', fieldtype='Select',
                 options='Collect on Delivery\nCredit', default='Collect on Delivery', insert_after='shipping_fee',
                 description='Collect on Delivery: thu đủ khi giao. Credit: ghi công nợ khách hàng trên hóa đơn.'),
            dict(fieldname='custom_payment_due_date', label='Hạn thanh toán công nợ', fieldtype='Date',
                 insert_after='custom_payment_policy', depends_on='eval:doc.custom_payment_policy == "Credit"'),
        ],
        'Sales Invoice': [link('custom_delivery_order', 'Đơn vận chuyển', 'Delivery Order'),
                          link('custom_delivery_trip', 'Chuyến vận chuyển', 'Delivery Trip')],
        'Payment Entry': [link('custom_delivery_confirmation', 'Phiếu giao nhận thu cước', 'Delivery Confirmation')],
        'Journal Entry': [link('custom_vehicle_log', 'Nhật ký chi phí nguồn', 'Vehicle Log'),
                          link('custom_delivery_trip', 'Chuyến vận chuyển', 'Delivery Trip')],
    }, update=True)
    # Accountants may inspect operational sources, never acquire driver/dispatch actions.
    from frappe.permissions import add_permission, update_permission_property
    for role in ('Accounts User', 'Accounts Manager'):
        for dt in ('Delivery Order', 'Delivery Trip', 'Delivery Confirmation', 'Vehicle Log'):
            add_permission(dt, role, 0)
            for right in ('read', 'select'):
                update_permission_property(dt, role, 0, right, 1)
    for dt, field in [('Sales Invoice', 'custom_delivery_order'), ('Sales Invoice', 'custom_delivery_trip'),
                      ('Payment Entry', 'custom_delivery_confirmation'), ('Journal Entry', 'custom_vehicle_log'),
                      ('Journal Entry', 'custom_delivery_trip')]:
        frappe.db.add_index(dt, [field, 'docstatus'])
