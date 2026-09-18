"""Member 1 only: fleet/dispatch metadata and fictional demo data.
No GPS, fuel, maintenance or delivery-confirmation tables are created.
"""
import json
from pathlib import Path
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.permissions import update_permission_property

CUSTOM_FIELDS={
 'Vehicle':[
    dict(fieldname='custom_payload_capacity_kg',label='Payload Capacity (kg)',fieldtype='Float',non_negative=1,insert_after='model'),
    dict(fieldname='custom_technical_status',label='Technical Status',fieldtype='Select',options='Available\nUnder Maintenance\nOut of Service',default='Available',insert_after='custom_payload_capacity_kg'),
 ],
 'Delivery Trip':[
    dict(fieldname='custom_expected_end_time',label='Expected End Time',fieldtype='Datetime',insert_after='departure_time'),
    dict(fieldname='custom_start_odometer',label='Start Odometer (km)',fieldtype='Int',non_negative=1,insert_after='custom_expected_end_time'),
    dict(fieldname='custom_end_odometer',label='End Odometer (km)',fieldtype='Int',non_negative=1,insert_after='custom_start_odometer'),
 ]
}

def install():
    company='Công ty Phân phối Đông Phong'
    if not frappe.db.exists('Company',company):
        raise RuntimeError('Expected Dong Phong company does not exist.')
    for dt,fields in CUSTOM_FIELDS.items():
        meta=frappe.get_meta(dt)
        for f in fields:
            old=meta.get_field(f['fieldname'])
            if old and (old.fieldtype!=f['fieldtype'] or (old.options or '')!=(f.get('options') or '')):
                raise RuntimeError('Field conflict: '+dt+'.'+f['fieldname'])
    create_custom_fields(CUSTOM_FIELDS,update=False)
    if not frappe.get_meta('Vehicle').allow_import:
        make_property_setter('Vehicle',None,'allow_import',1,'Check',for_doctype=True)
    update_permission_property('Vehicle','Fleet Manager',0,'import',1)
    frappe.clear_cache()
    frappe.db.commit()
    created=[]
    for plate,km in [('51C-234.56',18000),('51C-345.67',32000)]:
        if not frappe.db.exists('Vehicle',plate):
            doc=frappe.get_doc(dict(doctype='Vehicle',license_plate=plate,make='Isuzu',model='QKR',
                last_odometer=km,fuel_type='Diesel',uom='Litre',custom_technical_status='Available'))
            doc.insert();created.append(['Vehicle',doc.name])
    drivers=[]
    for full_name in ['Nguyễn Văn An','Trần Minh Bình','Lê Quốc Dũng']:
        existing=frappe.get_all('Driver',filters={'full_name':full_name},pluck='name')
        if len(existing)>1: raise RuntimeError('Ambiguous driver name: '+full_name)
        if existing: drivers.append(existing[0]);continue
        doc=frappe.get_doc(dict(doctype='Driver',full_name=full_name,status='Active',naming_series='HR-DRI-.YYYY.-'))
        doc.insert();drivers.append(doc.name);created.append(['Driver',doc.name])
    customer_title='DP DEMO - Điểm giao Bình Dương'
    customer=frappe.db.get_value('Customer',{'customer_name':customer_title},'name')
    if not customer:
        doc=frappe.get_doc(dict(doctype='Customer',customer_name=customer_title,customer_type='Company',
            customer_group='Commercial',territory='Vietnam'))
        doc.insert();customer=doc.name;created.append(['Customer',customer])
    address_title='DP DEMO - Địa chỉ giao Bình Dương'
    address=frappe.db.get_value('Address',{'address_title':address_title},'name')
    if not address:
        doc=frappe.get_doc(dict(doctype='Address',address_title=address_title,address_type='Shipping',
            address_line1='Điểm giao mô phỏng của nhóm Đông Phong',city='Bình Dương',country='Vietnam',
            links=[dict(link_doctype='Customer',link_name=customer)]))
        doc.insert();address=doc.name;created.append(['Address',address])
    trip=frappe.db.get_value('Delivery Stop',{'address':address,'parenttype':'Delivery Trip'},'parent')
    if not trip:
        date=frappe.utils.today()
        doc=frappe.get_doc(dict(doctype='Delivery Trip',company=company,vehicle='51C-123.45',
            driver=drivers[0],driver_name='Nguyễn Văn An',departure_time=date+' 08:00:00',
            custom_expected_end_time=date+' 12:00:00',custom_start_odometer=25000,
            naming_series='MAT-DT-.YYYY.-',status='Draft',
            delivery_stops=[dict(customer=customer,address=address)]))
        doc.insert();trip=doc.name;created.append(['Delivery Trip',trip])
    frappe.db.commit()
    out=Path('/tmp/dong-phong-schema');out.mkdir(exist_ok=True)
    names=['Company','Vehicle','Driver','Delivery Trip','Delivery Stop','Customer','Address','Dynamic Link']
    metadata={};ddl=[]
    for n in names:
        m=frappe.get_meta(n)
        metadata[n]={'fields':[dict(fieldname=f.fieldname,label=f.label,fieldtype=f.fieldtype,
            options=f.options,reqd=f.reqd) for f in m.fields if f.fieldtype not in ['Section Break','Column Break','Tab Break','HTML','Button']],
            'columns':frappe.db.sql('SHOW COLUMNS FROM `tab'+n+'`',as_dict=True)}
        ddl.append(frappe.db.sql('SHOW CREATE TABLE `tab'+n+'`')[0][1]+';')
    (out/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'schema-reference.sql').write_text('-- REFERENCE ONLY. Install using Frappe, not this SQL.\n\n'+'\n\n'.join(ddl),encoding='utf-8')
    result={'scope':'member_1_fleet_dispatch','created':created,'demo_trip':trip,
            'counts':{n:frappe.db.count(n) for n in ['Vehicle','Driver','Delivery Trip']},
            'vehicle_import_enabled':frappe.get_meta('Vehicle').allow_import}
    (out/'installation-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':
    install()
