"""V16 acceptance: real document lifecycle; failure cases roll back.

Run via bench Python from sites/. Set DP_ACCEPTANCE_COMMIT=1 to retain the
completed scenario. Names are synthetic business fixtures, never live customers.
No email/SMS is sent and no invoice/payment is posted.
"""
import json
import os

import frappe
from frappe.utils import now_datetime, add_to_date, today


def run():
    from dp_dispatch.api import make_delivery_order_from_quotation
    from dp_dispatch import completion, transport
    from dp_dispatch.delivery_confirmation import get_stop_details

    frappe.set_user('Administrator')
    frappe.flags.in_test = True
    checks = []
    company = frappe.get_all('Company', pluck='name')[0]
    now = now_datetime()
    start = add_to_date(now, minutes=-10)
    end = add_to_date(now, hours=3)
    def reject(label, fn, expected):
        user = frappe.session.user
        frappe.db.savepoint('negative_case')
        try:
            fn()
        except (frappe.ValidationError, frappe.PermissionError) as error:
            assert expected in str(error), (label, str(error))
            checks.append(label)
        else:
            raise AssertionError('Expected rejection: ' + label)
        finally:
            frappe.db.rollback(save_point='negative_case')
            frappe.set_user(user)
            frappe.clear_messages()

    def master(dt, name, values):
        if frappe.db.exists(dt, name):
            return frappe.get_doc(dt, name)
        return frappe.get_doc(dict(doctype=dt, **values)).insert()

    customer = master('Customer', 'Bao bì Nam Phước', dict(customer_name='Bao bì Nam Phước', customer_type='Company',
                       customer_group=frappe.get_all('Customer Group', filters={'is_group':0}, pluck='name')[0],
                       territory=frappe.get_all('Territory', filters={'is_group':0}, pluck='name')[0]))
    item = master('Item', 'VC-BAO-BI-CARTON', dict(item_code='VC-BAO-BI-CARTON', item_name='Vận chuyển thùng bao bì carton',
                  item_group=frappe.get_all('Item Group', filters={'is_group':0}, pluck='name')[0], stock_uom='Nos', is_stock_item=0,
                  weight_per_unit=6, weight_uom='Kg'))
    vehicle = master('Vehicle', '51D-728.46', dict(license_plate='51D-728.46', make='Isuzu', model='NPR 400',
                     last_odometer=48200, fuel_type='Diesel', uom='Litre', custom_payload_capacity_kg=3500, custom_technical_status='Available'))
    user_name = 'minh.tran@dongphong.example'
    if not frappe.db.exists('User', user_name):
        frappe.get_doc(dict(doctype='User', email=user_name, first_name='Trần', last_name='Quang Minh',
                            enabled=1, send_welcome_email=0, user_type='System User', roles=[{'role':'DP Driver'}])).insert()
    employee_name = frappe.db.get_value('Employee', {'user_id': user_name}, 'name')
    if not employee_name:
        master('Gender', 'Male', dict(gender='Male'))
        employee = frappe.get_doc(dict(doctype='Employee', naming_series='HR-EMP-', first_name='Trần Quang Minh',
                          gender='Male', date_of_birth='1990-05-12', date_of_joining='2025-01-06', status='Active',
                          company=company, user_id=user_name)).insert()
        employee_name = employee.name
    driver_name = frappe.db.get_value('Driver', {'employee': employee_name}, 'name')
    if not driver_name:
        driver_name = frappe.get_doc(dict(doctype='Driver', full_name='Trần Quang Minh', status='Active',
                                employee=employee_name, expiry_date='2030-05-12')).insert().name

    def order(qty=40, weight=6):
        q = frappe.get_doc(dict(doctype='Quotation', quotation_to='Customer', party_name=customer.name,
                  company=company, transaction_date=today(), valid_till=add_to_date(now, days=7).date(),
                  currency='VND', selling_price_list='Standard Selling',
                  items=[dict(item_code=item.name, qty=qty, rate=15000, uom='Nos', weight_per_unit=weight, weight_uom='Kg')])).insert()
        q.submit()
        reject('Báo giá chưa được khách đồng ý bị chặn', lambda: make_delivery_order_from_quotation(q.name), 'chưa')
        q.custom_customer_accepted = 1
        q.save()
        d = make_delivery_order_from_quotation(q.name)
        d.update(dict(sender_name='Nguyễn Hoài An', sender_phone='0900000128',
                      pickup_address='Kho Nam Phước, đường số 7, Khu công nghiệp Tân Tạo', pickup_city='TP. Hồ Chí Minh',
                      recipient_name='Lê Thanh Hương', recipient_phone='0900000146',
                      delivery_address='Kho phân phối Bình An, đường số 2, Khu công nghiệp Sóng Thần',
                      delivery_city='TP. Hồ Chí Minh', delivery_country='Vietnam',
                      pickup_window_start=start, pickup_window_end=end, pickup_service_minutes=15,
                      delivery_window_start=start, delivery_window_end=end, delivery_service_minutes=20,
                      instructions='Hàng carton đóng kiện, giữ khô; kiểm đếm tại điểm lấy và điểm giao.'))
        for row in d.items:
            row.weight_kg = weight
        d.insert()
        d.submit()
        d.reload()
        assert d.shipping_address and d.pickup_address_link
        assert frappe.db.get_value('Quotation',q.name,'delivery_order') == d.name
        return q, d

    q, d = order()
    checks.append('Quotation Submit → khách đồng ý → Delivery Order Submit; liên kết hai chiều và hai địa chỉ')
    reject('Chặn tạo đơn lặp từ báo giá', lambda: make_delivery_order_from_quotation(q.name), 'đã liên kết')

    def new_trip(orders):
        stops = []
        for index, document in enumerate(orders):
            pair = transport.order_stops(document.name)
            for offset, stop in enumerate(pair):
                stop['custom_planned_arrival'] = add_to_date(now, minutes=20 + index*50 + offset*25)
            stops.extend(pair)
        return frappe.get_doc(dict(doctype='Delivery Trip', company=company, vehicle=vehicle.name, driver=driver_name,
                   departure_time=start, custom_expected_end_time=end, custom_start_odometer=48200,
                   custom_transport_mode=transport.MODE, delivery_stops=stops))

    def wrong_sequence():
        t = new_trip([d]); t.delivery_stops.reverse(); t.insert()
    reject('Chặn giao trước lấy', wrong_sequence, 'Phải lấy')
    def wrong_window():
        t = new_trip([d]); t.delivery_stops[0].custom_planned_arrival=add_to_date(end,hours=1); t.insert()
    reject('Chặn giờ đến ngoài khung giờ', wrong_window, 'khung giờ')
    def wrong_service():
        t = new_trip([d]); t.delivery_stops[1].custom_planned_arrival=t.delivery_stops[0].custom_planned_arrival; t.insert()
    reject('Chặn bỏ qua thời gian phục vụ', wrong_service, 'thời gian phục vụ')

    # Sequential loads can exceed truck capacity in total, but not at any segment.
    frappe.db.savepoint('peak_case')
    _, a = order(200, 10); _, b = order(200, 10)
    sequential = new_trip([a,b]).insert()
    assert sequential.custom_planned_load_kg == 2000
    assert [s.custom_load_after_kg for s in sequential.delivery_stops] == [2000,0,2000,0]
    def overload():
        t=new_trip([a,b]); t.delivery_stops=[t.delivery_stops[i] for i in [0,2,1,3]]
        for idx,s in enumerate(t.delivery_stops): s.custom_planned_arrival=add_to_date(now,minutes=20+idx*25)
        t.insert()
    reject('Chặn quá tải ở một chặng',overload,'vượt tải trọng')
    frappe.db.rollback(save_point='peak_case')
    checks.append('Hai đơn tổng 4.000 kg, tải cao nhất 2.000 kg khi lấy–giao tuần tự')

    trip=new_trip([d]).insert(); trip.submit(); trip.reload()
    assert trip.status=='Scheduled'
    def wrong_driver():
        outsider=frappe.get_doc(dict(doctype='User', email='hung.le@dongphong.example',first_name='Lê Quốc Hưng',
                        enabled=1,send_welcome_email=0,user_type='System User',roles=[{'role':'DP Driver'}])).insert()
        frappe.set_user(outsider.name)
        get_stop_details(trip.name,trip.delivery_stops[0].name)
    reject('Tài xế khác không đọc/thao tác chuyến được phân',wrong_driver,'')
    reject('Chặn phân trùng đơn vào chuyến khác', lambda: new_trip([d]).insert(), 'Đơn đã được phân')
    reject('Chặn hủy đơn đã phân chuyến', lambda: frappe.get_doc('Delivery Order',d.name).cancel(), 'Đơn đã có chuyến')
    frappe.set_user(user_name)
    completion.start_trip(trip.name)
    trip.reload()
    assert trip.status=='In Transit'

    def confirm(stop, returned=0):
        details=get_stop_details(trip.name,stop.name)
        c=frappe.get_doc(dict(doctype='Delivery Confirmation',delivery_trip=trip.name,delivery_stop=stop.name,
                received_at=now_datetime(),recipient=d.sender_name if stop.custom_stop_type=='Pickup' else d.recipient_name,
                notes='Đã kiểm đếm số kiện và đối chiếu tình trạng bao bì.',
                shipping_fee_collected=details['shipping_fee'],fee_collection_method='Cash' if details['shipping_fee'] else None))
        for source in details['items']:
            row=dict(source,pending_qty=0,picked_up_qty=0,delivered_qty=0,returned_qty=0,returned_to_sender_qty=0)
            if stop.custom_stop_type=='Pickup': row['picked_up_qty']=source['allocated_qty']
            elif stop.custom_stop_type=='Delivery': row['delivered_qty']=source['allocated_qty']-returned; row['returned_qty']=returned
            else: row['returned_to_sender_qty']=source['allocated_qty']
            c.append('items',row)
        c.insert(); c.submit(); return c
    reject('Chặn xác nhận giao khi chưa lấy hàng',lambda:confirm(trip.delivery_stops[1]),'các điểm trước')
    pickup=confirm(trip.delivery_stops[0]); trip.reload()
    assert trip.custom_onboard_weight_kg==240
    reject('Chặn lấy trùng',lambda:confirm(trip.delivery_stops[0]),'đã có xác nhận')
    reject('Chặn hoàn tất khi còn hàng trên xe',lambda:completion.request_completion(trip.name),'còn hàng trên xe')
    reject('Tài xế không được tự duyệt hoàn tất',lambda:completion.approve_completion(trip.name),'')

    frappe.db.savepoint('partial_case')
    partial=confirm(trip.delivery_stops[1],returned=5)
    trip.reload(); assert trip.custom_onboard_weight_kg==30
    reject('Giao thiếu: hàng cần trả vẫn nằm trên xe',lambda:completion.request_completion(trip.name),'còn hàng trên xe')
    frappe.db.rollback(save_point='partial_case')

    delivery=confirm(trip.delivery_stops[1]); trip.reload()
    assert trip.custom_onboard_weight_kg==0
    completion.request_completion(trip.name)
    trip.reload(); assert trip.status!='Completed' and trip.custom_completion_status=='Requested'
    frappe.set_user('Administrator')
    reject('Không hủy phiếu lấy khi đã có phiếu giao',lambda:frappe.get_doc('Delivery Confirmation',pickup.name).cancel(),'các điểm sau')
    completion.approve_completion(trip.name)
    trip.reload(); d.reload(); q.reload()
    assert trip.status=='Completed' and trip.custom_completion_status=='Approved'
    assert d.delivery_status=='Delivered' and d.fee_status=='Paid'
    assert q.docstatus==d.docstatus==pickup.docstatus==delivery.docstatus==trip.docstatus==1
    reject('Chặn hủy phiếu sau khi duyệt hoàn tất',lambda:frappe.get_doc('Delivery Confirmation',delivery.name).cancel(),'hoàn tất')
    checks.append('Tài xế lấy 40 kiện/240 kg → giao đủ → thu 600.000 VND → yêu cầu → quản trị duyệt Completed')
    # Exercise a return-to-sender lifecycle separately, without retaining extra orders.
    frappe.db.savepoint('return_case')
    _, return_order=order()
    return_trip=new_trip([return_order])
    return_trip.append('delivery_stops',dict(custom_delivery_order=return_order.name,custom_stop_type='Return',
             custom_window_start=start,custom_window_end=end,custom_planned_arrival=add_to_date(now,minutes=90),custom_service_minutes=15,
             customer=return_order.customer,address=return_order.pickup_address_link,customer_address=return_order.pickup_address))
    return_trip.insert(); return_trip.submit(); return_trip.reload()
    saved_trip,saved_order=trip,d
    trip,d=return_trip,return_order
    frappe.set_user(user_name); completion.start_trip(trip.name); trip.reload()
    confirm(trip.delivery_stops[0]); confirm(trip.delivery_stops[1],returned=5)
    trip.reload(); assert trip.custom_onboard_weight_kg==30
    return_receipt=confirm(trip.delivery_stops[2]); trip.reload(); assert trip.custom_onboard_weight_kg==0
    frappe.set_user('Administrator')
    return_receipt.cancel(); trip.reload(); assert trip.custom_onboard_weight_kg==30
    frappe.set_user(user_name); confirm(trip.delivery_stops[2]); completion.request_completion(trip.name)
    frappe.set_user('Administrator'); completion.approve_completion(trip.name)
    trip.reload(); assert trip.status=='Completed'
    frappe.db.rollback(save_point='return_case')
    trip,d=saved_trip,saved_order
    checks.append('Giao một phần → trả người gửi → hủy phiếu trả khôi phục hàng trên xe → trả lại → hoàn tất')
    report=dict(checks=checks,quotation=q.name,order=d.name,trip=trip.name,pickup=pickup.name,delivery=delivery.name,
                customer=customer.name,vehicle=vehicle.name,driver=driver_name,weight_kg=240,fee=d.shipping_fee,
                status=trip.status,approval=trip.custom_completion_status,storage='MariaDB / Frappe DocTypes',
                fixture_data='Synthetic business scenario; no real customer transaction or accounting posting.')
    if os.environ.get('DP_ACCEPTANCE_COMMIT')=='1':
        frappe.db.commit()
        report['retained']=True
    else:
        frappe.db.rollback()
        report['retained']=False
    return report


if __name__=='__main__':
    frappe.init(site='logistics-v16.localhost',sites_path='/home/frappe/frappe-bench/sites')
    frappe.connect()
    try:
        print(json.dumps(run(),ensure_ascii=False,default=str))
    except Exception:
        frappe.db.rollback()
        raise
    finally:
        frappe.destroy()
