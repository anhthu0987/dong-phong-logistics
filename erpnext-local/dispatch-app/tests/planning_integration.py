"""Planning acceptance against real OSRM and MariaDB; default transaction rollback."""
import json
import os
import frappe
from frappe.utils import now_datetime,add_to_date
from dp_dispatch import planning

def run():
 frappe.set_user('Administrator');checks=[]
 source=frappe.get_doc('Delivery Order',frappe.get_all('Delivery Order',filters={'docstatus':1},pluck='name')[0])
 quote=frappe.copy_doc(frappe.get_doc('Quotation',source.quotation));quote.delivery_order=None;quote.custom_customer_accepted=1
 quote.transaction_date=now_datetime().date();quote.valid_till=add_to_date(now_datetime(),days=7).date();quote.insert();quote.submit()
 order=frappe.copy_doc(source);order.quotation=quote.name;order.shipping_address=None;order.pickup_address_link=None
 order.pickup_address='Điểm nhận hàng Đồng Khởi, Quận 1, TP. Hồ Chí Minh'
 order.delivery_address='Điểm giao hàng Bình Thạnh, TP. Hồ Chí Minh'
 order.delivery_status='Draft';order.fee_paid=0;order.fee_status='Unpaid'
 start=add_to_date(now_datetime(),hours=2);end=add_to_date(start,hours=10)
 for kind in ('pickup','delivery'):
  order.set(kind+'_window_start',start);order.set(kind+'_window_end',end)
 order.insert();order.submit();order.reload()
 for address,lat,lng in [(order.pickup_address_link,10.7769,106.7009),(order.shipping_address,10.8007,106.7117)]:
  frappe.db.set_value('Address',address,{'custom_latitude':lat,'custom_longitude':lng,'custom_routing_confirmed':1})
 v=frappe.get_all('Vehicle',filters={'custom_technical_status':'Available'},pluck='name')[0]
 d=frappe.get_all('Driver',filters={'status':'Active'},pluck='name')[0]
 plan=frappe.get_doc(dict(doctype='Transport Plan',title='Điều phối giao bao bì nội thành',company=quote.company,
  departure=start,end_time=end,orders=[dict(delivery_order=order.name)],vehicles=[dict(vehicle=v,driver=d,origin_lat=10.7769,origin_lng=106.7009,origin_confirmed=1)])).insert()
 if os.environ.get('DP_PLAN_QUEUE')=='1':
  planning.request_plan(plan.name);frappe.db.commit()
  return {'plan':plan.name,'status':'Queued','retained':True}
 data=planning.snapshot(plan)
 import requests
 result=requests.post('http://optimizer:8000/solve',json=data,headers={'X-Optimizer-Token':frappe.conf.optimizer_token},timeout=240)
 assert result.status_code==200,result.text
 result=result.json();assert result['status']=='Ready',result
 planning.validate_result(data,result)
 checks.append('OSRM thực → OR-Tools → lấy trước giao, đường đi và tải hợp lệ')
 planning.update(plan,status='Ready',version=1,snapshot=planning.dumps(data),input_hash=planning.digest(data),proposal=planning.dumps(result))
 frappe.db.savepoint('stale')
 frappe.db.set_value('Vehicle',v,'last_odometer',data['vehicles'][0]['odometer']+1)
 try:planning.approve_plan(plan.name)
 except frappe.ValidationError:checks.append('Chặn phương án cũ khi nguồn lực thay đổi')
 else:raise AssertionError('Stale plan accepted')
 frappe.db.rollback(save_point='stale')
 trips=planning.approve_plan(plan.name)
 assert planning.approve_plan(plan.name)==trips and len(trips)==1
 trip=frappe.get_doc('Delivery Trip',trips[0]);assert trip.docstatus==1 and trip.custom_transport_plan==plan.name
 checks.append('Duyệt phát hành Submit; duyệt lại không tạo chuyến trùng')
 from dp_dispatch.completion import start_trip
 start_trip(trip.name)
 checks.append('Chuyến phát hành nối được luồng bắt đầu vận chuyển')
 copied=frappe.copy_doc(trip)
 try:planning.require_plan(copied)
 except frappe.ValidationError:checks.append('Chặn phát hành chuyến ngoài kế hoạch')
 else:raise AssertionError('Manual release accepted')
 return {'checks':checks,'plan':plan.name,'trips':trips,'retained':False}

if __name__=='__main__':
 frappe.init(site='logistics-v16.localhost',sites_path='/home/frappe/frappe-bench/sites');frappe.connect()
 try:print(json.dumps(run(),ensure_ascii=False,default=str))
 finally:frappe.db.rollback();frappe.destroy()
