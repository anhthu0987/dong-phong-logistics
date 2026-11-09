import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def install():
    def field(n,l,t,**kw):return dict(fieldname=n,label=l,fieldtype=t,**kw)
    create_custom_fields({
      'Delivery Trip':[
        field('custom_transport_plan','Kế hoạch được duyệt','Link',options='Transport Plan',read_only=1,no_copy=1),
        field('custom_plan_version','Phiên bản kế hoạch','Int',read_only=1,no_copy=1),
        field('custom_planned_route','Tuyến OSRM được duyệt','Code',options='JSON',read_only=1,no_copy=1)],
      'Vehicle':[field('custom_routing_vehicle_type','Loại xe phục vụ điều phối','Data')],
      'Delivery Order':[field('custom_required_vehicle_type','Loại xe yêu cầu','Data')],
      'Address':[field('custom_routing_confirmed','Đã kiểm tra tọa độ dùng lập tuyến','Check',default=0)],
    },update=True)
