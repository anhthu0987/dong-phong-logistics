"""One row per trip; current ledger balances, filtered by departure dates."""
import frappe
from frappe.utils import flt, getdate, add_days
from dp_dispatch.accounting import require_accountant, unposted_collection


def execute(filters=None):
    require_accountant()
    filters = frappe._dict(filters or {})
    if not filters.company:
        frappe.throw('Chọn công ty để không cộng lẫn các đồng tiền.')
    if filters.from_date and filters.to_date and getdate(filters.from_date) > getdate(filters.to_date):
        frappe.throw('Khoảng ngày không hợp lệ.')
    query = {'company': filters.company, 'docstatus': 1}
    if filters.delivery_trip:
        query['name'] = filters.delivery_trip
    extra = []
    if filters.from_date:
        extra.append(['Delivery Trip', 'departure_time', '>=', filters.from_date])
    if filters.to_date:
        extra.append(['Delivery Trip', 'departure_time', '<', str(add_days(filters.to_date, 1))])
    # get_list applies document permissions AND user-permission restrictions.
    trips = frappe.get_list('Delivery Trip', filters=[['Delivery Trip', k, '=', v] for k, v in query.items()] + extra,
        fields=['name', 'vehicle', 'custom_completion_status'], limit_page_length=0, order_by='departure_time desc')
    currency = frappe.get_cached_value('Company', filters.company, 'default_currency')
    data = []
    for trip in trips:
        row = dict(delivery_trip=trip.name, vehicle=trip.vehicle, completion=trip.custom_completion_status, currency=currency)
        orders = set(frappe.get_all('Delivery Stop', filters={'parent': trip.name, 'parenttype': 'Delivery Trip'},
                                  pluck='custom_delivery_order')) - {None, ''}
        for o in orders:
            frappe.get_doc('Delivery Order', o).check_permission('read')
        row['agreed_fee'] = sum(flt(frappe.db.get_value('Delivery Order', o, 'shipping_fee')) for o in orders)
        invoices = frappe.get_all('Sales Invoice', filters={'custom_delivery_trip': trip.name, 'docstatus': 1},
            fields=['name', 'grand_total', 'base_net_total', 'outstanding_amount', 'is_return', 'custom_delivery_order'])
        for invoice in invoices:
            frappe.get_doc('Sales Invoice', invoice.name).check_permission('read')
        row['invoiced_total'] = sum(flt(i.grand_total) for i in invoices)
        row['revenue'] = sum(flt(i.base_net_total) for i in invoices)
        row['outstanding'] = sum(flt(i.outstanding_amount) for i in invoices)
        billed = {i.custom_delivery_order for i in invoices if not i.is_return}
        row['unbilled'] = sum(flt(frappe.db.get_value('Delivery Order', o, 'shipping_fee')) for o in orders - billed)
        row['posted_receipts'] = 0
        for invoice in invoices:
            row['posted_receipts'] += flt(frappe.db.sql("""SELECT COALESCE(SUM(
                CASE WHEN p.payment_type='Receive' THEN r.allocated_amount ELSE -r.allocated_amount END),0)
                FROM `tabPayment Entry Reference` r JOIN `tabPayment Entry` p ON p.name=r.parent
                WHERE p.docstatus=1 AND r.reference_doctype='Sales Invoice' AND r.reference_name=%s""", invoice.name)[0][0])
        row['declared_collected'] = flt(frappe.db.sql("""SELECT COALESCE(SUM(shipping_fee_collected),0)
            FROM `tabDelivery Confirmation` WHERE delivery_trip=%s AND docstatus=1""", trip.name)[0][0])
        row['unposted_collection'] = sum(unposted_collection(o) for o in orders)
        logs = frappe.get_all('Vehicle Log', filters={'custom_delivery_trip': trip.name, 'docstatus': 1,
            'custom_approval_status': 'Approved'}, fields=['name', 'custom_expense_amount'])
        row['approved_cost'] = sum(flt(log.custom_expense_amount) for log in logs)
        row['posted_cost'] = 0
        for log in logs:
            frappe.get_doc('Vehicle Log', log.name).check_permission('read')
            for dt, field in [('Journal Entry', 'custom_vehicle_log'), ('Expense Claim', 'vehicle_log')]:
                vouchers = frappe.get_all(dt, filters={field: log.name, 'docstatus': 1}, pluck='name')
                for voucher in vouchers:
                    frappe.get_doc(dt, voucher).check_permission('read')
                    row['posted_cost'] += flt(frappe.db.sql("""SELECT COALESCE(SUM(g.debit-g.credit),0)
                        FROM `tabGL Entry` g JOIN `tabAccount` a ON a.name=g.account
                        WHERE g.voucher_type=%s AND g.voucher_no=%s AND g.is_cancelled=0
                        AND a.root_type='Expense'""", (dt, voucher))[0][0])
        row['unposted_cost'] = row['approved_cost'] - row['posted_cost']
        row['margin'] = row['revenue'] - row['posted_cost']
        data.append(row)
    columns = [
        dict(fieldname='delivery_trip', label='Chuyến', fieldtype='Link', options='Delivery Trip', width=180),
        dict(fieldname='vehicle', label='Xe', fieldtype='Link', options='Vehicle', width=120),
        dict(fieldname='completion', label='Duyệt chuyến', fieldtype='Data', width=110),
        dict(fieldname='currency', label='Tiền tệ', fieldtype='Link', options='Currency', width=80),
    ]
    for key, label in [('agreed_fee','Cước thỏa thuận'), ('unbilled','Cước chưa xuất hóa đơn'),
        ('invoiced_total','Hóa đơn sau thuế (ròng)'), ('revenue','Doanh thu chưa thuế'),
        ('posted_receipts','Thu/hoàn qua Payment Entry'), ('outstanding','Công nợ hóa đơn'),
        ('declared_collected','Tài xế khai đã thu'), ('unposted_collection','Đã thu chưa hạch toán'),
        ('approved_cost','Chi phí đã duyệt'), ('posted_cost','Chi phí đã hạch toán'),
        ('unposted_cost','Chi phí chưa hạch toán'), ('margin','Lãi gộp đã hạch toán')]:
        columns.append(dict(fieldname=key, label=label, fieldtype='Currency', options='currency', width=170))
    message = ('Số dư hiện tại của các chuyến được chọn, không phải báo cáo số dư tại ngày quá khứ. '
               'Lãi gộp dùng doanh thu chưa thuế trừ chi phí đã hạch toán; chưa đủ nếu còn hóa đơn/chi phí chờ xử lý. '
               'Tiền tài xế khai đã thu không đồng nghĩa đã nộp về quỹ công ty. '
               'Công nợ lấy từ ERPNext, không tính lại bằng cước trừ tiền tài xế khai.')
    return columns, data, message
