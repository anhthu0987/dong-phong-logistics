"""Business workspaces; standard DocTypes keep their upstream module ownership."""
import json

import frappe


AREAS = (
    ('DP Sales', 'Khách hàng và báo giá', 'Selling', (
        ('Khách hàng', 'Customer'), ('Báo giá', 'Quotation'),
        ('Đơn dịch vụ', 'Sales Order'), ('Dịch vụ', 'Item'), ('Bảng giá', 'Item Price'),
    )),
    ('DP Transport Orders', 'Đơn vận chuyển', 'DP Transport Orders', (
        ('Đơn vận chuyển', 'Delivery Order'),
    )),
    ('DP Fleet Operations', 'Xe, tài xế và vận hành', 'DP Fleet Operations', (
        ('Xe', 'Vehicle'), ('Tài xế', 'Driver'), ('Nhân viên', 'Employee'),
        ('Nhật ký xe', 'Vehicle Log'), ('Hạng mục bảo dưỡng', 'Vehicle Service Item'),
        ('Kế hoạch bảo dưỡng', 'Fleet Maintenance Plan'),
        ('Ghi nhận bảo dưỡng', 'Fleet Maintenance Record'),
    )),
    ('DP Transport Planning', 'Điều phối và quản lý chuyến', 'DP Transport Planning', (
        ('Kế hoạch vận chuyển', 'Transport Plan'), ('Chuyến vận chuyển', 'Delivery Trip'),
    )),
    ('DP Tracking and POD', 'Theo dõi và giao nhận', 'DP Tracking and POD', (
        ('Xác nhận giao hàng', 'Delivery Confirmation'),
        ('Lịch sử GPS', 'GPS Log'), ('Thiết bị GPS', 'GPS Device'),
    )),
    ('DP Accounts', 'Hóa đơn, công nợ và báo cáo', 'Accounts', (
        ('Hóa đơn bán hàng', 'Sales Invoice'), ('Thanh toán', 'Payment Entry'),
        ('Hóa đơn mua hàng', 'Purchase Invoice'), ('Bút toán chi phí', 'Journal Entry'),
    )),
)


def _workspace(name, title, module, groups, sequence):
    doc = (frappe.get_doc('Workspace', name)
           if frappe.db.exists('Workspace', name) else frappe.new_doc('Workspace'))
    doc.name = name
    doc.label = name
    doc.title = name
    doc.module = module
    doc.type = 'Workspace'
    doc.icon = 'truck'
    doc.public = 1
    doc.is_hidden = 0
    doc.standard = 0
    doc.sequence_id = sequence
    doc.content = json.dumps([
        {'id': f'area_{index}', 'type': 'card', 'data': {'card_name': label, 'col': 4}}
        for index, (label, links) in enumerate(groups)
    ], ensure_ascii=False)
    doc.set('links', [])
    for label, links in groups:
        doc.append('links', {'type': 'Card Break', 'label': label})
        for caption, target, kind in links:
            if frappe.db.exists(kind, target):
                doc.append('links', {'type': 'Link', 'label': caption,
                                    'link_type': kind, 'link_to': target})
    doc.save(ignore_permissions=True)


def install_workspaces():
    def links_for(name, doctypes):
        links = [(label, dt, 'DocType') for label, dt in doctypes]
        if name == 'DP Tracking and POD':
            links += [('Bản đồ theo chuyến', 'fleet-map', 'Page'), ('Lịch trình tài xế', 'driver-gps', 'Page')]
        if name == 'DP Accounts':
            links += [('Đối soát vận tải', 'Transport Reconciliation', 'Report')]
        return links
    for index, (name, title, module, doctypes) in enumerate(AREAS):
        _workspace(name, title, module,
                   [(title, links_for(name, doctypes))], 51 + index)
    # Keep the existing landing URL as a hub, without owning business DocTypes.
    # Workspace Link in Frappe v15 accepts DocType/Page/Report, not Workspace.
    # The six independent workspaces also appear in the Desk workspace list.
    _workspace('DP Dispatch', 'Đông Phong Logistics', 'DP Dispatch', [
        (title, links_for(name, doctypes))
        for name, title, _, doctypes in AREAS
    ], 50)


def install_sidebar():
    if not frappe.db.exists('DocType', 'Sidebar'):
        return
    doc = (frappe.get_doc('Sidebar', 'DP Dispatch')
           if frappe.db.exists('Sidebar', 'DP Dispatch') else frappe.new_doc('Sidebar'))
    doc.title = 'DP Dispatch'
    doc.module = 'DP Dispatch'
    doc.app = 'dp_dispatch'
    doc.header_icon = 'truck'
    doc.standard = 0
    doc.set('items', [])
    for name, label in [('DP Dispatch', 'Trang chủ')] + [(a[0], a[1]) for a in AREAS]:
        doc.append('items', {'type': 'Link', 'label': label,
                            'link_type': 'Workspace', 'link_to': name, 'icon': 'truck'})
    doc.save(ignore_permissions=True)
