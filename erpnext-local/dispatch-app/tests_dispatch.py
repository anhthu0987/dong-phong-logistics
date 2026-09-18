"""Integration checks using real Document insert/submit/cancel; rollback all test data."""
import json
import frappe
from frappe.utils import add_days, today

def run():
    results=[]
    original_counts={dt:frappe.db.count(dt) for dt in ['Vehicle','Driver','Delivery Trip']}
    original_user=frappe.session.user
    frappe.set_user('Administrator')
    frappe.db.savepoint('dispatch_suite')
    try:
        vehicles=[];drivers=[]
        for i in range(3):
            v=frappe.get_doc(dict(doctype='Vehicle',license_plate='DP-TEST-'+frappe.generate_hash(length=8),
                make='Simulation',model='Test',last_odometer=1000,fuel_type='Diesel',uom='Litre',
                custom_payload_capacity_kg=2000,custom_technical_status='Available')).insert()
            vehicles.append(v.name)
            drivers.append(frappe.get_doc(dict(doctype='Driver',full_name='DP TEST '+str(i),status='Active',naming_series='HR-DRI-.YYYY.-')).insert().name)
        template=frappe.get_doc('Delivery Trip','MAT-DT-2026-00001')
        date=add_days(today(),10)
        def trip(vi=0,di=0,start='08:00:00',end='12:00:00',load=1000):
            return frappe.get_doc(dict(doctype='Delivery Trip',naming_series='MAT-DT-.YYYY.-',company=template.company,
                vehicle=vehicles[vi],driver=drivers[di],departure_time=date+' '+start,
                custom_expected_end_time=date+' '+end,custom_planned_load_kg=load,
                custom_start_odometer=1000,
                delivery_stops=[dict(customer=s.customer,address=s.address) for s in template.delivery_stops]))
        def reject(label,code,fn):
            frappe.db.savepoint('rejected_case')
            try: fn()
            except frappe.ValidationError as e:
                if '['+code+']' not in str(e): raise
                results.append(label)
            else: raise AssertionError('Expected rejection: '+label)
            finally: frappe.db.rollback(save_point='rejected_case')
        valid=trip().insert();valid.submit()
        assert valid.docstatus==1 and valid.status=='Scheduled'
        results.append('Valid trip inserts and submits')
        reject('Same vehicle overlap blocked','DP_CONFLICT',lambda:trip(di=1).insert())
        reject('Same driver overlap blocked','DP_CONFLICT',lambda:trip(vi=1).insert())
        other=trip(vi=1,di=1).insert();other.submit();results.append('Different resources may overlap')
        boundary=trip(start='12:00:00',end='14:00:00').insert();boundary.submit();results.append('Adjacent intervals accepted')
        reject('Reversed time rejected','DP_TIME',lambda:trip(vi=2,di=2,start='12:00:00',end='08:00:00').insert())
        reject('Equal timestamps rejected','DP_TIME',lambda:trip(vi=2,di=2,start='08:00:00',end='08:00:00').insert())
        reject('Overload rejected','DP_OVERLOAD',lambda:trip(vi=2,di=2,load=2001).insert())
        def no_end():
            d=trip(vi=2,di=2);d.custom_expected_end_time=None;d.insert();d.submit()
        reject('Missing end cannot submit','DP_REQUIRED',no_end)
        reject('Missing load cannot submit','DP_LOAD_REQUIRED',lambda:trip(vi=2,di=2,load=0).insert().submit())
        def no_capacity():
            frappe.db.set_value('Vehicle',vehicles[2],'custom_payload_capacity_kg',0)
            trip(vi=2,di=2).insert().submit()
        reject('Unknown capacity cannot submit','DP_LOAD_REQUIRED',no_capacity)
        def unavailable():
            frappe.db.set_value('Vehicle',vehicles[2],'custom_technical_status','Under Maintenance')
            trip(vi=2,di=2).insert()
        reject('Maintenance vehicle rejected','DP_UNAVAILABLE',unavailable)
        def inactive():
            frappe.db.set_value('Driver',drivers[2],'status','Suspended')
            trip(vi=2,di=2).insert()
        reject('Inactive driver rejected','DP_DRIVER',inactive)
        def expired():
            frappe.db.set_value('Driver',drivers[2],'expiry_date',add_days(date,-1))
            trip(vi=2,di=2).insert()
        reject('Expired licence rejected','DP_LICENSE',expired)
        def km_bad():
            d=trip(vi=2,di=2);d.custom_end_odometer=999;d.insert()
        reject('Odometer regression rejected','DP_ODOMETER',km_bad)
        def km_after_submit():
            d=frappe.get_doc('Delivery Trip',valid.name);d.custom_end_odometer=999;d.save()
        reject('Odometer checked after submit','DP_ODOMETER',km_after_submit)
        draft1=trip(vi=2,di=2).insert();draft2=trip(vi=2,di=2).insert()
        results.append('Drafts do not reserve resources')
        draft1.submit()
        reject('Submit rechecks conflict','DP_CONFLICT',lambda:draft2.submit())
        valid.cancel()
        replacement=trip().insert();replacement.submit();results.append('Cancellation releases reservation')
        for stop in replacement.delivery_stops: stop.visited=1
        replacement.save();assert replacement.status=='Completed'
        trip().insert().submit();results.append('Completed trip releases reservation')
    finally:
        frappe.db.rollback(save_point='dispatch_suite')
        frappe.set_user(original_user)
    assert original_counts=={dt:frappe.db.count(dt) for dt in original_counts}
    result={'passed':len(results),'checks':results,'test_data_rolled_back':True}
    print(json.dumps(result,ensure_ascii=False))
    return result

run()
