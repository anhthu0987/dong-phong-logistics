"""
Dong Phong Logistics - System Schema & Demo Data Installation.
Integrated: Member 1 (Fleet/Dispatch) & Member 2 (Operations, Delivery Confirmation, Maintenance & Fuel).
Strictly non-destructive: Safe checks for all existing doctypes and data.
"""
import json
from pathlib import Path
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.permissions import update_permission_property


CUSTOM_FIELDS = {
    'Vehicle': [
        dict(fieldname='custom_payload_capacity_kg', label='Payload Capacity (kg)', fieldtype='Float', non_negative=1, insert_after='model'),
        dict(fieldname='custom_technical_status', label='Technical Status', fieldtype='Select', options='Available\nUnder Maintenance\nOut of Service', default='Available', insert_after='custom_payload_capacity_kg'),
    ],
    'Delivery Trip': [
        dict(fieldname='custom_expected_end_time', label='Expected End Time', fieldtype='Datetime', insert_after='departure_time'),
        dict(fieldname='custom_start_odometer', label='Start Odometer (km)', fieldtype='Int', non_negative=1, insert_after='custom_expected_end_time'),
        dict(fieldname='custom_end_odometer', label='End Odometer (km)', fieldtype='Int', non_negative=1, insert_after='custom_start_odometer'),
    ]
}

def create_delivery_confirmation_doctypes():
    """Tự động tạo bảng Delivery Confirmation Item (Child) và Delivery Confirmation (Parent)"""
    module = 'Dong Phong Operations'
    if not frappe.db.exists('Module Def', module):
        frappe.get_doc(dict(doctype='Module Def', module_name=module, app_name='operations_app')).insert(ignore_permissions=True)

    # Delivery Confirmation Item
    if not frappe.db.exists('DocType', 'Delivery Confirmation Item'):
        child_doc = frappe.get_doc({
            'doctype': 'DocType',
            'name': 'Delivery Confirmation Item',
            'module': module,
            'custom': 1,
            'istable': 1,
            'fields': [
                {'fieldname': 'item_code', 'label': 'Item Code', 'fieldtype': 'Link', 'options': 'Item', 'reqd': 1, 'in_list_view': 1},
                {'fieldname': 'allocated_qty', 'label': 'Allocated Qty', 'fieldtype': 'Float', 'default': '0', 'in_list_view': 1},
                {'fieldname': 'received_qty', 'label': 'Received Qty', 'fieldtype': 'Float', 'default': '0', 'in_list_view': 1},
                {'fieldname': 'returned_qty', 'label': 'Returned Qty', 'fieldtype': 'Float', 'default': '0', 'in_list_view': 1},
                {'fieldname': 'pending_qty', 'label': 'Pending Qty', 'fieldtype': 'Float', 'default': '0', 'in_list_view': 1}
            ]
        })
        child_doc.insert(ignore_permissions=True)

    #Delivery Confirmation
    if not frappe.db.exists('DocType', 'Delivery Confirmation'):
        parent_doc = frappe.get_doc({
            'doctype': 'DocType',
            'name': 'Delivery Confirmation',
            'module': module,
            'custom': 1,
            'is_submittable': 1,
            'naming_rule': 'By "Naming Series" field',
            'autoname': 'naming_series:',
            'fields': [
                {'fieldname': 'naming_series', 'label': 'Series', 'fieldtype': 'Select', 'options': 'DP-DC-.YYYY.-', 'default': 'DP-DC-.YYYY.-', 'reqd': 1},
                {'fieldname': 'delivery_trip', 'label': 'Delivery Trip', 'fieldtype': 'Link', 'options': 'Delivery Trip', 'reqd': 1, 'in_list_view': 1},
                {'fieldname': 'delivery_stop', 'label': 'Delivery Stop reference', 'fieldtype': 'Data'},
                {'fieldname': 'section_break_received', 'fieldtype': 'Section Break', 'label': 'Received Information'},
                {'fieldname': 'received_time', 'label': 'Received Time', 'fieldtype': 'Datetime'},
                {'fieldname': 'received_by', 'label': 'Received By', 'fieldtype': 'Data', 'in_list_view': 1},
                {'fieldname': 'proof', 'label': 'Proof', 'fieldtype': 'Attach'},
                {'fieldname': 'section_break_items', 'fieldtype': 'Section Break', 'label': 'Items'},
                {'fieldname': 'items', 'label': 'Items', 'fieldtype': 'Table', 'options': 'Delivery Confirmation Item', 'reqd': 1}
            ],
            'permissions': [
                {'role': 'System Manager', 'read': 1, 'write': 1, 'create': 1, 'submit': 1, 'cancel': 1, 'delete': 1},
                {'role': 'Stock User', 'read': 1, 'write': 1, 'create': 1, 'submit': 1}
            ]
        })
        parent_doc.insert(ignore_permissions=True)

def create_maintenance_doctypes():
    """Tự động tạo Fleet Maintenance Plan và Fleet Maintenance Record"""
    module = 'Dong Phong Operations'
    if not frappe.db.exists('Module Def', module):
        frappe.get_doc(dict(doctype='Module Def', module_name=module, app_name='operations_app')).insert(ignore_permissions=True)

    # Fleet Maintenance Plan
    if not frappe.db.exists('DocType', 'Fleet Maintenance Plan'):
        plan_doc = frappe.get_doc({
            'doctype': 'DocType',
            'name': 'Fleet Maintenance Plan',
            'module': module,
            'custom': 1,
            'naming_rule': 'By "Naming Series" field',
            'autoname': 'naming_series:',
            'fields': [
                {'fieldname': 'naming_series', 'label': 'Series', 'fieldtype': 'Select', 'options': 'DP-MP-.YYYY.-', 'default': 'DP-MP-.YYYY.-', 'reqd': 1},
                {'fieldname': 'vehicle', 'label': 'Vehicle', 'fieldtype': 'Link', 'options': 'Vehicle', 'reqd': 1, 'in_list_view': 1},
                {'fieldname': 'service_item', 'label': 'Service Item', 'fieldtype': 'Data', 'reqd': 1, 'in_list_view': 1},
                {'fieldname': 'interval_km', 'label': 'Interval (km)', 'fieldtype': 'Int', 'default': 5000},
                {'fieldname': 'interval_days', 'label': 'Interval (Days)', 'fieldtype': 'Int', 'default': 90},
                {'fieldname': 'next_due_date', 'label': 'Next Due Date', 'fieldtype': 'Date'}
            ],
            'permissions': [
                {'role': 'System Manager', 'read': 1, 'write': 1, 'create': 1, 'delete': 1},
                {'role': 'Fleet Manager', 'read': 1, 'write': 1, 'create': 1}
            ]
        })
        plan_doc.insert(ignore_permissions=True)

    # Fleet Maintenance Record
    if not frappe.db.exists('DocType', 'Fleet Maintenance Record'):
        record_doc = frappe.get_doc({
            'doctype': 'DocType',
            'name': 'Fleet Maintenance Record',
            'module': module,
            'custom': 1,
            'is_submittable': 1,
            'naming_rule': 'By "Naming Series" field',
            'autoname': 'naming_series:',
            'fields': [
                {'fieldname': 'naming_series', 'label': 'Series', 'fieldtype': 'Select', 'options': 'DP-MR-.YYYY.-', 'default': 'DP-MR-.YYYY.-', 'reqd': 1},
                {'fieldname': 'maintenance_plan', 'label': 'Maintenance Plan', 'fieldtype': 'Link', 'options': 'Fleet Maintenance Plan', 'in_list_view': 1},
                {'fieldname': 'vehicle', 'label': 'Vehicle', 'fieldtype': 'Link', 'options': 'Vehicle', 'reqd': 1, 'in_list_view': 1},
                {'fieldname': 'performed_at', 'label': 'Performed At', 'fieldtype': 'Datetime', 'reqd': 1, 'in_list_view': 1},
                {'fieldname': 'accepted', 'label': 'Accepted (Nghiệm thu)', 'fieldtype': 'Check', 'default': 1, 'in_list_view': 1},
                {'fieldname': 'notes', 'label': 'Notes', 'fieldtype': 'Small Text'}
            ],
            'permissions': [
                {'role': 'System Manager', 'read': 1, 'write': 1, 'create': 1, 'submit': 1, 'cancel': 1, 'delete': 1},
                {'role': 'Fleet Manager', 'read': 1, 'write': 1, 'create': 1, 'submit': 1}
            ]
        })
        record_doc.insert(ignore_permissions=True)

def install():
    company = 'Công ty Phân phối Đông Phong'
    if not frappe.db.exists('Company', company):
        raise RuntimeError('Expected Dong Phong company does not exist.')

    # Tạo Custom Fields chuẩn của nhóm
    for dt, fields in CUSTOM_FIELDS.items():
        meta = frappe.get_meta(dt)
        for f in fields:
            old = meta.get_field(f['fieldname'])
            if old and (old.fieldtype != f['fieldtype'] or (old.options or '') != (f.get('options') or '')):
                raise RuntimeError('Field conflict: ' + dt + '.' + f['fieldname'])
    create_custom_fields(CUSTOM_FIELDS, update=False)

    if not frappe.get_meta('Vehicle').allow_import:
        make_property_setter('Vehicle', None, 'allow_import', 1, 'Check', for_doctype=True)
    update_permission_property('Vehicle', 'Fleet Manager', 0, 'import', 1)

    
    create_delivery_confirmation_doctypes()
    create_maintenance_doctypes()

    frappe.clear_cache()
    frappe.db.commit()

    created = []

    # Xe demo
    for plate, km in [('51C-123.45', 15000), ('51C-234.56', 18000), ('51C-345.67', 32000)]:
        if not frappe.db.exists('Vehicle', plate):
            doc = frappe.get_doc(dict(
                doctype='Vehicle', license_plate=plate, make='Isuzu', model='QKR',
                last_odometer=km, fuel_type='Diesel', uom='Litre', custom_technical_status='Available'
            ))
            doc.insert()
            created.append(['Vehicle', doc.name])

    # Tài xế demo
    drivers = []
    for full_name in ['Nguyễn Văn An', 'Trần Minh Bình', 'Lê Quốc Dũng']:
        existing = frappe.get_all('Driver', filters={'full_name': full_name}, pluck='name')
        if len(existing) > 1:
            raise RuntimeError('Ambiguous driver name: ' + full_name)
        if existing:
            drivers.append(existing[0])
            continue
        doc = frappe.get_doc(dict(doctype='Driver', full_name=full_name, status='Active', naming_series='HR-DRI-.YYYY.-'))
        doc.insert()
        drivers.append(doc.name)
        created.append(['Driver', doc.name])

    # Khách hàng & Điểm giao demo
    customer_title = 'DP DEMO - Điểm giao Bình Dương'
    customer = frappe.db.get_value('Customer', {'customer_name': customer_title}, 'name')
    if not customer:
        doc = frappe.get_doc(dict(
            doctype='Customer', customer_name=customer_title, customer_type='Company',
            customer_group='Commercial', territory='Vietnam'
        ))
        doc.insert()
        customer = doc.name
        created.append(['Customer', customer])

    address_title = 'DP DEMO - Địa chỉ giao Bình Dương'
    address = frappe.db.get_value('Address', {'address_title': address_title}, 'name')
    if not address:
        doc = frappe.get_doc(dict(
            doctype='Address', address_title=address_title, address_type='Shipping',
            address_line1='Điểm giao mô phỏng của nhóm Đông Phong', city='Bình Dương', country='Vietnam',
            links=[dict(link_doctype='Customer', link_name=customer)]
        ))
        doc.insert()
        address = doc.name
        created.append(['Address', address])

    # Chuyến giao demo
    trip = frappe.db.get_value('Delivery Stop', {'address': address, 'parenttype': 'Delivery Trip'}, 'parent')
    if not trip:
        date = frappe.utils.today()
        doc = frappe.get_doc(dict(
            doctype='Delivery Trip', company=company, vehicle='51C-123.45',
            driver=drivers[0], driver_name='Nguyễn Văn An', departure_time=date + ' 08:00:00',
            custom_expected_end_time=date + ' 12:00:00', custom_start_odometer=25000,
            naming_series='MAT-DT-.YYYY.-', status='Draft',
            delivery_stops=[dict(customer=customer, address=address)]
        ))
        doc.insert()
        trip = doc.name
        created.append(['Delivery Trip', trip])

    # Mặt hàng demo 
    item_code = 'HANG-01'
    if not frappe.db.exists('Item', item_code):
        doc = frappe.get_doc(dict(
            doctype='Item', item_code=item_code, item_name='Hàng Hóa Phân Phối 01',
            item_group='All Item Groups', stock_uom='Nos', is_stock_item=1
        ))
        doc.insert(ignore_permissions=True)
        created.append(['Item', item_code])

    # Phiếu xác nhận giao hàng demo 
    dc_name = frappe.db.get_value('Delivery Confirmation', {'delivery_trip': trip}, 'name')
    if not dc_name:
        dc_doc = frappe.get_doc({
            'doctype': 'Delivery Confirmation',
            'delivery_trip': trip,
            'delivery_stop': 'Kho Binh Duong',
            'received_time': frappe.utils.now_datetime(),
            'received_by': 'Nguyễn Văn A',
            'items': [{
                'item_code': item_code,
                'allocated_qty': 10,
                'received_qty': 8,
                'returned_qty': 2,
                'pending_qty': 0
            }]
        })
        dc_doc.insert(ignore_permissions=True)
        dc_name = dc_doc.name
        created.append(['Delivery Confirmation', dc_name])

    # Kế hoạch & Bản ghi bảo trì demo 
    vehicle_plate = '51C-123.45'
    plan_name = frappe.db.get_value('Fleet Maintenance Plan', {'vehicle': vehicle_plate}, 'name')
    if not plan_name:
        plan = frappe.get_doc({
            'doctype': 'Fleet Maintenance Plan',
            'vehicle': vehicle_plate,
            'service_item': 'Thay nhớt & bảo dưỡng định kỳ',
            'interval_km': 5000,
            'interval_days': 90,
            'next_due_date': frappe.utils.add_days(frappe.utils.today(), 30)
        })
        plan.insert(ignore_permissions=True)
        plan_name = plan.name
        created.append(['Fleet Maintenance Plan', plan_name])

    record_name = frappe.db.get_value('Fleet Maintenance Record', {'vehicle': vehicle_plate}, 'name')
    if not record_name:
        rec = frappe.get_doc({
            'doctype': 'Fleet Maintenance Record',
            'maintenance_plan': plan_name,
            'vehicle': vehicle_plate,
            'performed_at': frappe.utils.now_datetime(),
            'accepted': 1,
            'notes': 'Đã hoàn tất bảo dưỡng cấp 1 tại trạm Isuzu Bình Dương.'
        })
        rec.insert(ignore_permissions=True)
        record_name = rec.name
        created.append(['Fleet Maintenance Record', record_name])

    frappe.db.commit()

    # Xuất schema metadata ra file
    out = Path('/tmp/dong-phong-schema')
    out.mkdir(exist_ok=True)
    names = [
        'Company', 'Vehicle', 'Driver', 'Delivery Trip', 'Delivery Stop',
        'Customer', 'Address', 'Dynamic Link', 
        'Delivery Confirmation', 'Delivery Confirmation Item',
        'Fleet Maintenance Plan', 'Fleet Maintenance Record'
    ]
    metadata = {}
    ddl = []
    for n in names:
        if frappe.db.exists('DocType', n):
            m = frappe.get_meta(n)
            metadata[n] = {
                'fields': [
                    dict(fieldname=f.fieldname, label=f.label, fieldtype=f.fieldtype, options=f.options, reqd=f.reqd)
                    for f in m.fields if f.fieldtype not in ['Section Break', 'Column Break', 'Tab Break', 'HTML', 'Button']
                ],
                'columns': frappe.db.sql('SHOW COLUMNS FROM `tab' + n + '`', as_dict=True)
            }
            ddl.append(frappe.db.sql('SHOW CREATE TABLE `tab' + n + '`')[0][1] + ';')

    (out / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
    (out / 'schema-reference.sql').write_text('-- REFERENCE ONLY. Install using Frappe, not this SQL.\n\n' + '\n\n'.join(ddl), encoding='utf-8')

    result = {
        'scope': 'full_dong_phong_logistics',
        'created': created,
        'demo_trip': trip,
        'demo_delivery_confirmation': dc_name,
        'demo_maintenance_record': record_name,
        'counts': {n: frappe.db.count(n) for n in ['Vehicle', 'Driver', 'Delivery Trip', 'Delivery Confirmation', 'Fleet Maintenance Record']},
        'vehicle_import_enabled': frappe.get_meta('Vehicle').allow_import
    }
    (out / 'installation-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))

if __name__ == '__main__':
    install()