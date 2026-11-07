import json
import frappe
from frappe.utils.modules import get_module_placement
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def install():
    create_custom_fields({
        'Vehicle':[
            dict(fieldname='custom_payload_capacity_kg',label='Tải trọng (kg)',fieldtype='Float',non_negative=1,insert_after='model',description='Tải trọng tối đa của xe; phải lớn hơn khối lượng hàng của chuyến.'),
            dict(fieldname='custom_technical_status',label='Tình trạng kỹ thuật',fieldtype='Select',options='Available\nUnder Maintenance\nOut of Service',default='Available',insert_after='custom_payload_capacity_kg',description='Chỉ xe ở trạng thái Available mới được phân chuyến.'),
        ],
        'Delivery Trip':[
            dict(fieldname='custom_expected_end_time',label='Thời gian kết thúc dự kiến',fieldtype='Datetime',insert_after='departure_time',description='Bắt buộc trước khi xác nhận chuyến; có thể trùng giờ kết thúc chuyến trước.'),
            dict(fieldname='custom_start_odometer',label='Số km lúc khởi hành',fieldtype='Int',non_negative=1,insert_after='custom_expected_end_time'),
            dict(fieldname='custom_end_odometer',label='Số km lúc kết thúc',fieldtype='Int',non_negative=1,allow_on_submit=1,insert_after='custom_start_odometer',description='Cập nhật sau khi biết số km cuối; phải lớn hơn hoặc bằng số km đầu.'),
            dict(fieldname='custom_planned_load_kg',label='Khối lượng hàng (kg)',fieldtype='Float',non_negative=1,insert_after='custom_end_odometer',description='Tự tính từ các đơn vận chuyển được gắn vào chuyến.'),
            dict(fieldname='custom_vehicle_capacity_kg',label='Tải trọng xe (kg)',fieldtype='Float',fetch_from='vehicle.custom_payload_capacity_kg',read_only=1,insert_after='custom_planned_load_kg'),
            dict(fieldname='custom_total_delivery_qty',label='Tổng số lượng cần giao',fieldtype='Data',read_only=1,allow_on_submit=1,insert_after='custom_vehicle_capacity_kg'),
            dict(fieldname='custom_started_at',label='Actual Start Time',fieldtype='Datetime',read_only=1,allow_on_submit=1,insert_after='custom_total_delivery_qty'),
            dict(fieldname='custom_started_by',label='Started By',fieldtype='Link',options='User',read_only=1,allow_on_submit=1,insert_after='custom_started_at'),
            dict(fieldname='custom_completion_status',label='Trip Completion Approval',fieldtype='Select',options='Open\nRequested\nApproved\nRejected\nException Requested\nException Closed',default='Open',read_only=1,allow_on_submit=1,insert_after='custom_vehicle_capacity_kg'),
            dict(fieldname='custom_completion_requested_at',label='Completion Requested At',fieldtype='Datetime',read_only=1,allow_on_submit=1,insert_after='custom_completion_status'),
            dict(fieldname='custom_completion_requested_by',label='Completion Requested By',fieldtype='Link',options='User',read_only=1,allow_on_submit=1,insert_after='custom_completion_requested_at'),
            dict(fieldname='custom_completion_review_note',label='Completion Review Note',fieldtype='Small Text',read_only=1,allow_on_submit=1,insert_after='custom_completion_requested_by'),
            dict(fieldname='custom_completed_at',label='Approved Completion At',fieldtype='Datetime',read_only=1,allow_on_submit=1,insert_after='custom_completion_review_note'),
            dict(fieldname='custom_completed_by',label='Approved By',fieldtype='Link',options='User',read_only=1,allow_on_submit=1,insert_after='custom_completed_at'),
        ],
        'Delivery Stop':[
            dict(fieldname='custom_delivery_order',label='Đơn vận chuyển',fieldtype='Link',options='Delivery Order',in_list_view=1,insert_after='delivery_note',description='Chọn đơn vận chuyển đã Submit; hệ thống tự điền khách hàng và địa chỉ giao.'),
            dict(fieldname='custom_delivery_state',label='Tiến độ giao',fieldtype='Select',options='Assigned\nIn Transit\nDelivered\nPartial\nReturned\nException',default='Assigned',read_only=1,allow_on_submit=1,insert_after='custom_delivery_order'),
        ],
        'Vehicle Log':[
            dict(fieldname='custom_delivery_trip',label='Chuyến vận chuyển',fieldtype='Link',options='Delivery Trip',insert_after='license_plate',description='Liên kết chi phí nhiên liệu/bảo dưỡng với chuyến sử dụng xe này.'),
            dict(fieldname='custom_expense_section',label='Chi phí phát sinh trong chuyến',fieldtype='Section Break',insert_after='custom_delivery_trip'),
            dict(fieldname='custom_expense_type',label='Loại chi phí',fieldtype='Select',options='Fuel\nRoad Toll\nParking\nEmergency Repair\nOther',insert_after='custom_expense_section'),
            dict(fieldname='custom_expense_amount',label='Số tiền chi phí',fieldtype='Currency',non_negative=1,default=0,insert_after='custom_expense_type'),
            dict(fieldname='custom_expense_note',label='Diễn giải chi phí',fieldtype='Small Text',insert_after='custom_expense_amount'),
            dict(fieldname='custom_receipt',label='Hóa đơn / chứng từ',fieldtype='Attach',insert_after='custom_expense_note'),
            dict(fieldname='custom_approval_status',label='Trạng thái duyệt chi phí',fieldtype='Select',options='Draft\nPending Review\nNeeds Correction\nApproved\nRejected',default='Draft',read_only=1,in_list_view=1,insert_after='custom_receipt'),
            dict(fieldname='custom_submitted_for_review_at',label='Gửi duyệt lúc',fieldtype='Datetime',read_only=1,insert_after='custom_approval_status'),
            dict(fieldname='custom_review_note',label='Ý kiến Admin',fieldtype='Small Text',read_only=1,allow_on_submit=1,insert_after='custom_submitted_for_review_at'),
            dict(fieldname='custom_reviewed_by',label='Admin xử lý',fieldtype='Link',options='User',read_only=1,allow_on_submit=1,insert_after='custom_review_note'),
            dict(fieldname='custom_reviewed_at',label='Xử lý lúc',fieldtype='Datetime',read_only=1,allow_on_submit=1,insert_after='custom_reviewed_by'),
        ],
    },update=True)
    create_custom_fields({
        'Delivery Order': [
            dict(fieldname='quotation',label='Báo giá nguồn',fieldtype='Link',options='Quotation',insert_after='customer',read_only=1,description='Báo giá khách đã xác nhận; dùng để đối chiếu cước và dịch vụ.'),
        ],
        'Quotation': [
            dict(fieldname='custom_customer_accepted',label='Khách hàng đã đồng ý báo giá',fieldtype='Check',default=0,allow_on_submit=1,insert_after='customer_name',description='Chỉ đánh dấu sau khi khách xác nhận đồng ý. Trạng thái Open chỉ có nghĩa báo giá còn mở, không đồng nghĩa khách đã chấp nhận.'),
            dict(fieldname='delivery_order',label='Đơn vận chuyển được tạo',fieldtype='Link',options='Delivery Order',read_only=1,allow_on_submit=1,insert_after='custom_customer_accepted',description='Đơn vận chuyển được tạo từ báo giá này; dòng hàng được liên kết với từng Quotation Item.'),
        ],
        'Delivery Order Item': [
            dict(fieldname='quotation_item',label='Dòng báo giá nguồn',fieldtype='Link',options='Quotation Item',hidden=1,read_only=1),
        ],
        'Delivery Confirmation': [
            dict(fieldname='delivery_order',label='Đơn vận chuyển',fieldtype='Link',options='Delivery Order',read_only=1,insert_after='delivery_note'),
            dict(fieldname='shipping_fee_due',label='Cước cần thu',fieldtype='Currency',read_only=1,insert_after='recipient'),
            dict(fieldname='shipping_fee_collected',label='Cước đã thu',fieldtype='Currency',default=0,non_negative=1,insert_after='shipping_fee_due'),
            dict(fieldname='fee_collection_method',label='Phương thức thu cước',fieldtype='Select',options='Cash\nBank Transfer\nE-wallet',insert_after='shipping_fee_collected'),
            dict(fieldname='fee_collected_by',label='Người thu cước',fieldtype='Link',options='User',read_only=1,insert_after='fee_collection_method'),
            dict(fieldname='fee_collected_at',label='Thời điểm thu cước',fieldtype='Datetime',read_only=1,insert_after='fee_collected_by'),
        ],
        'Delivery Confirmation Item': [
            dict(fieldname='delivery_order_item',label='Dòng hàng đơn vận chuyển',fieldtype='Link',options='Delivery Order Item',hidden=1),
            dict(fieldname='delivery_order_item_ref',label='Mã dòng hàng đơn vận chuyển',fieldtype='Data',hidden=1),
            dict(fieldname='item_code_display',label='Mã hàng',fieldtype='Data',read_only=1,in_list_view=1),
            dict(fieldname='description',label='Mô tả hàng',fieldtype='Data',read_only=1,in_list_view=1),
        ],
    },update=True)
    sync_existing_quotation_delivery_order_links()
    from dp_dispatch.permissions import install_permissions
    install_permissions()
    install_client_script('DP Dispatch Delivery Order', 'Delivery Order', 'delivery_order.js')
    install_client_script('DP Dispatch Delivery Confirmation', 'Delivery Confirmation', 'delivery_confirmation.js')
    install_client_script('DP Dispatch Quotation', 'Quotation', 'quotation.js')
    install_client_script('DP Dispatch Fleet Maintenance Record', 'Fleet Maintenance Record', 'fleet_maintenance_record.js')
    install_client_script('DP Dispatch Vehicle Log', 'Vehicle Log', 'vehicle_log.js')
    install_dispatch_workspace()
    install_dispatch_sidebar()
    frappe.db.add_index('Delivery Trip',['vehicle','departure_time'],'dp_vehicle_departure')
    frappe.db.add_index('Delivery Trip',['driver','departure_time'],'dp_driver_departure')
    frappe.clear_cache()


def sync_existing_quotation_delivery_order_links():
    """Backfill the reverse link for active orders created before two-way linking existed."""
    orders = frappe.get_all(
        "Delivery Order",
        filters={"quotation": ["is", "set"], "docstatus": ["!=", 2]},
        fields=["name", "quotation"],
        order_by="creation asc",
    )
    for order in orders:
        if not frappe.db.get_value("Quotation", order.quotation, "delivery_order"):
            frappe.db.set_value("Quotation", order.quotation, "delivery_order", order.name, update_modified=False)

def install_client_script(name, doctype, filename):
    if not frappe.db.exists('DocType', doctype):
        return
    script = frappe.get_doc('Client Script', name) if frappe.db.exists('Client Script', name) else frappe.new_doc('Client Script')
    script.name = name
    script.dt = doctype
    script.view = 'Form'
    script.enabled = 1
    with open(frappe.get_app_path('dp_dispatch', 'public', 'js', filename), encoding='utf-8') as source:
        script.script = source.read()
    script.save(ignore_permissions=True)


def install_dispatch_workspace():
    """Create a stable, grouped entry point for the four demo business areas."""
    groups = [
        ("Khách hàng và báo giá", [
            ("Khách hàng", "Customer"),
            ("Báo giá", "Quotation"),
            ("Dịch vụ vận chuyển", "Item"),
            ("Bảng giá dịch vụ", "Item Price"),
        ]),
        ("Đơn vận chuyển", [
            ("Đơn vận chuyển", "Delivery Order"),
        ]),
        ("Xe, tài xế và vận hành", [
            ("Xe", "Vehicle"),
            ("Tài xế", "Driver"),
            ("Nhân viên", "Employee"),
            ("Nhật ký xe", "Vehicle Log"),
            ("Hạng mục bảo dưỡng xe", "Vehicle Service Item"),
            ("Kế hoạch bảo dưỡng", "Fleet Maintenance Plan"),
            ("Ghi nhận bảo dưỡng", "Fleet Maintenance Record"),
        ]),
        ("Điều phối và quản lý chuyến", [
            ("Chuyến vận chuyển", "Delivery Trip"),
            ("Xác nhận giao hàng", "Delivery Confirmation"),
        ]),
    ]
    workspace = frappe.get_doc("Workspace", "DP Dispatch") if frappe.db.exists("Workspace", "DP Dispatch") else frappe.new_doc("Workspace")
    workspace.label = "DP Dispatch"
    workspace.title = "DP Dispatch"
    workspace.module = "DP Dispatch"
    workspace.type = "Workspace"
    workspace.icon = "truck"
    workspace.public = 1
    workspace.is_hidden = 0
    workspace.standard = 0
    workspace.sequence_id = 50
    workspace.content = json.dumps([
        {"id": "dp_dispatch_sales", "type": "card", "data": {"card_name": "Khách hàng và báo giá", "col": 3}},
        {"id": "dp_dispatch_orders", "type": "card", "data": {"card_name": "Đơn vận chuyển", "col": 3}},
        {"id": "dp_dispatch_fleet", "type": "card", "data": {"card_name": "Xe, tài xế và vận hành", "col": 3}},
        {"id": "dp_dispatch_trips", "type": "card", "data": {"card_name": "Điều phối và quản lý chuyến", "col": 3}},
    ], ensure_ascii=False)
    workspace.links = []
    for group, doctypes in groups:
        workspace.append("links", {"type": "Card Break", "label": group})
        for label, doctype in doctypes:
            if frappe.db.exists("DocType", doctype):
                workspace.append("links", {
                    "type": "Link",
                    "label": label,
                    "link_type": "DocType",
                    "link_to": doctype,
                })
    workspace.save(ignore_permissions=True)


def install_dispatch_sidebar():
    """Expose the same four business areas in the DP Dispatch left navigation."""
    groups = [
        ("Khách hàng và báo giá", [
            ("Khách hàng", "Customer", "user-round"),
            ("Báo giá", "Quotation", "file-text"),
            ("Dịch vụ vận chuyển", "Item", "package"),
            ("Bảng giá dịch vụ", "Item Price", "tag"),
        ]),
        ("Đơn vận chuyển", [
            ("Đơn vận chuyển", "Delivery Order", "truck"),
        ]),
        ("Xe, tài xế và vận hành", [
            ("Xe", "Vehicle", "truck"),
            ("Tài xế", "Driver", "user-round"),
            ("Nhân viên", "Employee", "users-round"),
            ("Nhật ký xe", "Vehicle Log", "clipboard-list"),
            ("Hạng mục bảo dưỡng xe", "Vehicle Service Item", "wrench"),
            ("Kế hoạch bảo dưỡng", "Fleet Maintenance Plan", "calendar-check"),
            ("Ghi nhận bảo dưỡng", "Fleet Maintenance Record", "clipboard-check"),
        ]),
        ("Điều phối và quản lý chuyến", [
            ("Chuyến vận chuyển", "Delivery Trip", "route"),
            ("Xác nhận giao hàng", "Delivery Confirmation", "circle-check"),
        ]),
    ]

    sidebar = frappe.get_doc("Sidebar", "DP Dispatch") if frappe.db.exists("Sidebar", "DP Dispatch") else frappe.new_doc("Sidebar")
    sidebar.title = "DP Dispatch"
    sidebar.module = "DP Dispatch"
    sidebar.app = get_module_placement("DP Dispatch")
    sidebar.header_icon = "truck"
    sidebar.standard = 0
    sidebar.items = []
    sidebar.append("items", {
        "type": "Link",
        "label": "Trang chủ",
        "link_type": "Workspace",
        "link_to": "DP Dispatch",
        "icon": "house",
    })
    for group, doctypes in groups:
        sidebar.append("items", {
            "type": "Section Break",
            "label": group,
            "indent": 1,
            "collapsible": 1,
            "keep_closed": 0,
        })
        for label, doctype, icon in doctypes:
            if frappe.db.exists("DocType", doctype):
                sidebar.append("items", {
                    "type": "Link",
                    "label": label,
                    "link_type": "DocType",
                    "link_to": doctype,
                    "icon": icon,
                    "child": 1,
                })
    sidebar.save(ignore_permissions=True)
