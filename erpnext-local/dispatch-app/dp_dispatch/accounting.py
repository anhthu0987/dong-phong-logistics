"""Transport sources link to standard ERPNext accounting documents.

Factories save drafts with normal permissions. Only standard submit/cancel posts
or reverses the GL. Source locks serialize duplicate create/submit attempts.
"""
import frappe
from frappe.utils import flt, today

EPS = 0.000001
ACCOUNTING_ROLES = {'Accounts User', 'Accounts Manager', 'System Manager'}


def require_accountant():
    if frappe.session.user != 'Administrator' and not ACCOUNTING_ROLES.intersection(frappe.get_roles()):
        frappe.throw('Chỉ nhân viên kế toán được lập chứng từ đối soát.', frappe.PermissionError)


def fail(message):
    frappe.throw('[DP_ACCOUNTS] ' + message)


def lock_source(doctype, name):
    # Doctype is always an internal constant, never an API argument.
    if doctype not in ('Delivery Order', 'Delivery Confirmation', 'Vehicle Log', 'Sales Invoice'):
        raise ValueError(doctype)
    frappe.db.sql(f'SELECT name FROM `tab{doctype}` WHERE name=%s FOR UPDATE', name)
    return frappe.get_doc(doctype, name)


def existing(doctype, field, source, exclude=None, extra=None):
    filters = {field: source, 'docstatus': ['!=', 2]}
    if exclude:
        filters['name'] = ['!=', exclude]
    filters.update(extra or {})
    return frappe.db.get_value(doctype, filters, 'name')


def check_unique(doc, field, source, extra=None):
    if existing(doc.doctype, field, source, doc.name, extra):
        fail('Nguồn đã có chứng từ kế toán còn hiệu lực; mở chứng từ cũ hoặc hủy trước khi lập lại.')


def source_order(name, trip_name):
    order = lock_source('Delivery Order', name)
    trip = frappe.get_doc('Delivery Trip', trip_name)
    if order.docstatus != 1 or trip.docstatus != 1 or trip.custom_completion_status != 'Approved':
        fail('Chỉ lập hóa đơn cho đơn đã Submit thuộc chuyến đã duyệt hoàn tất.')
    if not any(s.get('custom_delivery_order') == name for s in trip.delivery_stops):
        fail('Đơn không thuộc chuyến trên hóa đơn.')
    quotation = frappe.get_doc('Quotation', order.quotation)
    return order, trip, quotation


def account_details(name, company, currency):
    a = frappe.get_doc('Account', name)
    if a.company != company or a.is_group or a.disabled or a.account_currency != currency:
        fail('Tài khoản phải hoạt động, không phải nhóm, cùng công ty và đồng tiền chứng từ.')
    return a


def unposted_collection(order_name):
    rows = frappe.db.sql('''SELECT c.name, c.shipping_fee_collected,
        COALESCE(SUM(p.received_amount),0) posted
        FROM `tabDelivery Confirmation` c
        LEFT JOIN `tabPayment Entry` p ON p.custom_delivery_confirmation=c.name AND p.docstatus=1
        WHERE c.delivery_order=%s AND c.docstatus=1
        GROUP BY c.name,c.shipping_fee_collected''', order_name, as_dict=True)
    return sum(max(0, flt(r.shipping_fee_collected) - flt(r.posted)) for r in rows)


@frappe.whitelist(methods=['POST'])
def make_invoice(order_name, trip_name):
    require_accountant()
    order, trip, quotation = source_order(order_name, trip_name)
    order.check_permission('read')
    trip.check_permission('read')
    old = existing('Sales Invoice', 'custom_delivery_order', order.name, extra={'is_return': 0})
    if old:
        frappe.get_doc('Sales Invoice', old).check_permission('read')
        return old
    if flt(order.shipping_fee) <= 0:
        fail('Đơn không có cước; không tạo hóa đơn giá trị 0.')
    if quotation.currency != frappe.get_cached_value('Company', quotation.company, 'default_currency'):
        fail('Tích hợp hiện hỗ trợ cước bằng đồng tiền công ty; cần xử lý tỷ giá trước khi lập hóa đơn ngoại tệ.')
    invoice = frappe.new_doc('Sales Invoice')
    invoice.update({
        'company': quotation.company, 'customer': order.customer,
        'currency': quotation.currency, 'conversion_rate': 1,
        'posting_date': today(), 'due_date': order.get('custom_payment_due_date') or today(),
        'custom_delivery_order': order.name, 'custom_delivery_trip': trip.name,
        'selling_price_list': quotation.selling_price_list,
        'ignore_pricing_rule': 1, 'disable_rounded_total': 1,
        'apply_discount_on': quotation.get('apply_discount_on') or 'Grand Total',
        'additional_discount_percentage': quotation.get('additional_discount_percentage') or 0,
        'discount_amount': quotation.get('discount_amount') or 0,
        'taxes_and_charges': quotation.get('taxes_and_charges'),
        'remarks': f'Cước vận chuyển đơn {order.name}, chuyến {trip.name}.',
    })
    # The quotation contains sold transport services, NOT the cargo ledger.
    for row in quotation.items:
        if frappe.get_cached_value('Item', row.item_code, 'is_stock_item'):
            fail('Báo giá chứa hàng tồn kho. Cần tách dịch vụ vận tải khỏi hàng chở trước khi xuất hóa đơn.')
        invoice.append('items', {k: row.get(k) for k in (
            'item_code', 'item_name', 'description', 'qty', 'uom', 'stock_uom',
            'conversion_factor', 'rate', 'price_list_rate', 'discount_percentage',
            'discount_amount', 'item_tax_template')})
    for row in quotation.get('taxes', []):
        invoice.append('taxes', {k: row.get(k) for k in (
            'charge_type', 'row_id', 'account_head', 'description', 'rate',
            'tax_amount', 'included_in_print_rate', 'cost_center', 'included_in_paid_amount')})
    invoice.insert()
    return invoice.name


def validate_invoice(doc, method=None):
    if doc.get('return_against'):
        original = frappe.get_doc('Sales Invoice', doc.return_against)
        if original.get('custom_delivery_order'):
            if doc.get('custom_delivery_order') and doc.custom_delivery_order != original.custom_delivery_order:
                fail('Đơn trên hóa đơn điều chỉnh không khớp hóa đơn gốc.')
            doc.custom_delivery_order = original.custom_delivery_order
            doc.custom_delivery_trip = original.custom_delivery_trip
    preserve_source(doc, ['custom_delivery_order', 'custom_delivery_trip'])
    if not doc.get('custom_delivery_order'):
        if doc.get('custom_delivery_trip'):
            fail('Hóa đơn vận tải cần cả đơn và chuyến.')
        return
    require_accountant()
    order, trip, quote = source_order(doc.custom_delivery_order, doc.custom_delivery_trip)
    if doc.is_return:
        original = frappe.get_doc('Sales Invoice', doc.return_against) if doc.return_against else None
        if not original or original.docstatus != 1 or original.custom_delivery_order != order.name or original.custom_delivery_trip != trip.name:
            fail('Hóa đơn điều chỉnh phải tham chiếu hóa đơn gốc của cùng đơn/chuyến.')
    else:
        check_unique(doc, 'custom_delivery_order', order.name, {'is_return': 0})
        if abs(flt(doc.grand_total) - flt(order.shipping_fee)) > EPS:
            fail('Tổng hóa đơn sau thuế/chiết khấu phải bằng cước đã thỏa thuận trên đơn. Kiểm tra báo giá nguồn.')
    if doc.company != quote.company or doc.customer != order.customer or doc.currency != quote.currency:
        fail('Công ty, khách hàng và đồng tiền hóa đơn phải khớp báo giá/đơn.')
    if doc.currency != frappe.get_cached_value('Company', doc.company, 'default_currency') or flt(doc.conversion_rate) != 1:
        fail('Chưa hỗ trợ hóa đơn vận tải ngoại tệ.')
    if doc.update_stock or doc.is_pos or doc.get('write_off_amount') or doc.get('loyalty_amount'):
        fail('Hóa đơn cước không xuất kho, không dùng POS hoặc xóa nợ tự động; thu tiền qua Payment Entry.')
    if not doc.disable_rounded_total:
        fail('Tắt làm tròn tổng để đối chiếu đúng cước của đơn.')


@frappe.whitelist(methods=['POST'])
def make_collection_payment(confirmation_name, paid_to, reference_no=None):
    require_accountant()
    confirmation = lock_source('Delivery Confirmation', confirmation_name)
    confirmation.check_permission('read')
    if confirmation.docstatus != 1 or flt(confirmation.shipping_fee_collected) <= 0:
        fail('Phiếu giao nhận phải Submit và có tiền thực thu.')
    old = existing('Payment Entry', 'custom_delivery_confirmation', confirmation.name)
    if old:
        frappe.get_doc('Payment Entry', old).check_permission('read')
        return old
    invoice_name = frappe.db.get_value('Sales Invoice', {
        'custom_delivery_order': confirmation.delivery_order, 'docstatus': 1, 'is_return': 0}, 'name')
    if not invoice_name:
        fail('Cần Submit hóa đơn cước trước khi hạch toán tiền thu.')
    invoice = lock_source('Sales Invoice', invoice_name)
    invoice.check_permission('read')
    account = account_details(paid_to, invoice.company, invoice.currency)
    if account.account_type not in ('Cash', 'Bank'):
        fail('Chọn tài khoản tiền mặt (kể cả quỹ tài xế giữ) hoặc ngân hàng thực nhận.')
    fee = flt(confirmation.shipping_fee_collected)
    if fee > flt(invoice.outstanding_amount) + EPS:
        fail('Tiền trên phiếu vượt công nợ hóa đơn còn lại; kiểm tra thu trùng hoặc hóa đơn điều chỉnh.')
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    payment = get_payment_entry('Sales Invoice', invoice.name, party_amount=fee, bank_account=paid_to, bank_amount=fee)
    payment.custom_delivery_confirmation = confirmation.name
    payment.reference_no = reference_no
    payment.reference_date = today()
    payment.insert()
    return payment.name


def validate_payment(doc, method=None):
    preserve_source(doc, ['custom_delivery_confirmation'])
    source = doc.get('custom_delivery_confirmation')
    if not source:
        for ref in doc.get('references', []):
            if ref.reference_doctype != 'Sales Invoice':
                continue
            invoice = frappe.get_doc('Sales Invoice', ref.reference_name)
            if invoice.get('custom_delivery_order') and doc.payment_type == 'Receive':
                lock_source('Sales Invoice', invoice.name)
                if unposted_collection(invoice.custom_delivery_order) > EPS:
                    fail('Còn tiền thu trên phiếu giao nhận chưa hạch toán. Lập Payment Entry từ phiếu đó trước để tránh thu trùng.')
        return
    require_accountant()
    c = lock_source('Delivery Confirmation', source)
    check_unique(doc, 'custom_delivery_confirmation', source)
    if c.docstatus != 1 or flt(c.shipping_fee_collected) <= 0:
        fail('Phiếu thu nguồn không còn hợp lệ.')
    if doc.payment_type != 'Receive' or doc.party_type != 'Customer' or len(doc.references) != 1:
        fail('Tiền thu giao nhận phải là Receive cho Customer, phân bổ đúng một hóa đơn.')
    ref = doc.references[0]
    if ref.reference_doctype != 'Sales Invoice':
        fail('Tiền thu giao nhận chỉ đối trừ Sales Invoice.')
    invoice = lock_source('Sales Invoice', ref.reference_name)
    if invoice.docstatus != 1 or invoice.is_return or invoice.custom_delivery_order != c.delivery_order or invoice.custom_delivery_trip != c.delivery_trip:
        fail('Hóa đơn không khớp đơn/chuyến trên phiếu giao nhận.')
    if doc.party != invoice.customer or doc.company != invoice.company or doc.paid_from != invoice.debit_to:
        fail('Khách hàng, công ty hoặc tài khoản phải thu không khớp hóa đơn.')
    fee = flt(c.shipping_fee_collected)
    if any(abs(flt(v) - fee) > EPS for v in (doc.paid_amount, doc.received_amount, ref.allocated_amount)):
        fail('Số tiền nhận và phân bổ phải bằng số tiền thực thu trên phiếu giao nhận.')
    a = account_details(doc.paid_to, doc.company, invoice.currency)
    if a.account_type not in ('Cash', 'Bank') or doc.deductions or doc.get('taxes'):
        fail('Không gộp khấu trừ/thuế vào tiền thực thu; chọn tài khoản tiền thực nhận.')
    if doc.paid_from_account_currency != invoice.currency or flt(doc.source_exchange_rate) != 1 or flt(doc.target_exchange_rate) != 1:
        fail('Tiền thu phải cùng đồng tiền hóa đơn, tỷ giá bằng 1.')


@frappe.whitelist(methods=['POST'])
def make_expense_entry(vehicle_log, expense_account, offset_account, cost_center):
    require_accountant()
    log = lock_source('Vehicle Log', vehicle_log)
    log.check_permission('read')
    old = existing('Journal Entry', 'custom_vehicle_log', log.name)
    if old:
        frappe.get_doc('Journal Entry', old).check_permission('read')
        return old
    if log.docstatus != 1 or log.custom_approval_status != 'Approved' or not log.custom_delivery_trip:
        fail('Nhật ký chi phí phải được duyệt/Submit và gắn chuyến.')
    company = frappe.db.get_value('Delivery Trip', log.custom_delivery_trip, 'company')
    amount = flt(log.custom_expense_amount)
    if amount <= 0:
        fail('Nhật ký không có số tiền chi phí hợp lệ.')
    entry = frappe.new_doc('Journal Entry')
    entry.update({'company': company, 'posting_date': today(), 'voucher_type': 'Journal Entry',
                  'custom_vehicle_log': log.name, 'custom_delivery_trip': log.custom_delivery_trip,
                  'user_remark': f'Chi phí {log.custom_expense_type}: {log.custom_expense_note or log.name}'})
    entry.append('accounts', {'account': expense_account, 'debit_in_account_currency': amount, 'cost_center': cost_center})
    entry.append('accounts', {'account': offset_account, 'credit_in_account_currency': amount})
    entry.insert()
    return entry.name


def validate_expense_entry(doc, method=None):
    preserve_source(doc, ['custom_vehicle_log', 'custom_delivery_trip'])
    if not doc.get('custom_vehicle_log'):
        if doc.get('custom_delivery_trip'):
            fail('Bút toán chi phí chuyến phải có nhật ký Vehicle Log nguồn.')
        return
    require_accountant()
    log = lock_source('Vehicle Log', doc.custom_vehicle_log)
    check_unique(doc, 'custom_vehicle_log', log.name)
    if existing('Expense Claim', 'vehicle_log', log.name):
        fail('Nhật ký đã có Expense Claim. Không ghi thêm bút toán chi phí cho cùng khoản.')
    trip = frappe.get_doc('Delivery Trip', log.custom_delivery_trip)
    if log.docstatus != 1 or log.custom_approval_status != 'Approved' or trip.docstatus != 1:
        fail('Chi phí nguồn/chuyến chưa hợp lệ hoặc đã hủy.')
    if doc.company != trip.company or doc.custom_delivery_trip != trip.name or log.license_plate != trip.vehicle:
        fail('Công ty, chuyến, xe của chi phí không khớp.')
    if len(doc.accounts) != 2 or doc.multi_currency or doc.get('is_opening') == 'Yes':
        fail('Bút toán chi phí gồm hai dòng, cùng đồng tiền công ty và không phải số dư đầu kỳ.')
    currency = frappe.get_cached_value('Company', doc.company, 'default_currency')
    debits = [r for r in doc.accounts if flt(r.debit_in_account_currency) > 0]
    credits = [r for r in doc.accounts if flt(r.credit_in_account_currency) > 0]
    if len(debits) != 1 or len(credits) != 1 or debits[0] is credits[0]:
        fail('Cần một dòng ghi Nợ chi phí và một dòng ghi Có đối ứng.')
    debit, credit = debits[0], credits[0]
    amount = flt(log.custom_expense_amount)
    if amount <= 0 or any(abs(flt(v) - amount) > EPS for v in (debit.debit_in_account_currency, credit.credit_in_account_currency)):
        fail('Số tiền hạch toán phải bằng chi phí được duyệt.')
    expense = account_details(debit.account, doc.company, currency)
    offset = account_details(credit.account, doc.company, currency)
    if expense.root_type != 'Expense':
        fail('Dòng Nợ phải là tài khoản chi phí.')
    if not (offset.account_type in ('Cash', 'Bank') or (offset.root_type == 'Liability' and offset.account_type != 'Payable')):
        fail('Đối ứng là tiền đã chi hoặc khoản phải hoàn ứng khác; không dùng công nợ nhà cung cấp thiếu chứng từ.')
    if not debit.cost_center or frappe.db.get_value('Cost Center', debit.cost_center, 'company') != doc.company or frappe.db.get_value('Cost Center', debit.cost_center, 'is_group'):
        fail('Chọn trung tâm chi phí chi tiết thuộc cùng công ty.')
    if any(r.get('party') or r.get('reference_type') or flt(r.exchange_rate) != 1 for r in doc.accounts):
        fail('Không gộp đối trừ công nợ hoặc tỷ giá vào bút toán chi phí chuyến.')


def guard_source_cancel(doc, method=None):
    lock_source(doc.doctype, doc.name)
    mapping = {
        'Delivery Order': ('Sales Invoice', 'custom_delivery_order'),
        'Delivery Trip': ('Sales Invoice', 'custom_delivery_trip'),
        'Delivery Confirmation': ('Payment Entry', 'custom_delivery_confirmation'),
        'Vehicle Log': ('Journal Entry', 'custom_vehicle_log'),
    }
    target, field = mapping[doc.doctype]
    if existing(target, field, doc.name):
        fail('Xử lý/hủy chứng từ kế toán liên kết trước khi hủy chứng từ nguồn.')
    if doc.doctype == 'Delivery Trip' and existing('Journal Entry', 'custom_delivery_trip', doc.name):
        fail('Xử lý bút toán chi phí trước khi hủy chuyến.')


def validate_expense_claim(doc, method=None):
    preserve_source(doc, ['vehicle_log'])
    if not doc.get('vehicle_log'):
        return
    log = lock_source('Vehicle Log', doc.vehicle_log)
    if log.get('custom_delivery_trip'):
        if existing('Journal Entry', 'custom_vehicle_log', log.name):
            fail('Nhật ký đã có bút toán chi phí. Không tạo thêm Expense Claim cho cùng khoản.')
        if log.docstatus != 1 or log.custom_approval_status != 'Approved':
            fail('Nhật ký chi phí phải được duyệt trước khi lập hoàn ứng.')
        if method == 'before_submit' and abs(flt(doc.total_sanctioned_amount) - flt(log.custom_expense_amount)) > EPS:
            fail('Hoàn ứng phải bằng chi phí chuyến được duyệt; không gộp khoản khác vào cùng nhật ký.')


def preserve_source(doc, fields):
    previous = doc.get_doc_before_save()
    if previous:
        for field in fields:
            if previous.get(field) and previous.get(field) != doc.get(field):
                fail('Không được gỡ hoặc đổi liên kết nguồn kế toán đã lưu; hủy và lập lại chứng từ.')
