"""ERPNext integration acceptance; always rolls back all generated documents."""
import json
import sys
from pathlib import Path
import frappe
from frappe.utils import flt, today
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from acceptance_transport import run as transport_run
from dp_dispatch import accounting
from dp_dispatch.dp_dispatch.report.transport_reconciliation.transport_reconciliation import execute


def run():
    checks = []
    scenario = transport_run(finalize=False, payment_policy='Credit', collection_fraction=1/3)
    frappe.set_user('Administrator')
    trip = frappe.get_doc('Delivery Trip', scenario['trip'])
    company = frappe.get_doc('Company', trip.company)
    assert company.default_currency == 'VND'
    cash = frappe.db.get_value('Account', dict(company=company.name, account_type='Cash',
        account_currency='VND', is_group=0, disabled=0), 'name')
    assert cash and company.default_expense_account and company.cost_center, 'Configure company accounts first'

    def row():
        data = execute(dict(company=company.name, delivery_trip=trip.name))[1]
        assert len(data) == 1
        return data[0]

    def reject(fn):
        frappe.db.savepoint('accounts_negative')
        try:
            fn()
        except (frappe.ValidationError, frappe.PermissionError):
            pass
        else:
            raise AssertionError('Expected rejection')
        finally:
            frappe.db.rollback(save_point='accounts_negative')
            frappe.clear_messages()

    name = accounting.make_invoice(scenario['order'], trip.name)
    assert accounting.make_invoice(scenario['order'], trip.name) == name
    invoice = frappe.get_doc('Sales Invoice', name)
    invoice.submit(); invoice.reload()
    assert flt(invoice.outstanding_amount) == 600000
    assert row()['unposted_collection'] == 200000
    checks.append('Credit trip completed; invoice receivable 600000; driver collection 200000 unposted')
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

    def direct_payment(value):
        p = get_payment_entry('Sales Invoice', name, party_amount=value, bank_account=cash, bank_amount=value)
        p.insert(); p.submit()
        return p

    reject(lambda: direct_payment(200000))
    receipt_name = accounting.make_collection_payment(scenario['delivery'], cash)
    assert accounting.make_collection_payment(scenario['delivery'], cash) == receipt_name
    receipt = frappe.get_doc('Payment Entry', receipt_name); receipt.submit()
    invoice.reload()
    assert flt(invoice.outstanding_amount) == 400000
    assert row()['unposted_collection'] == 0 and row()['posted_receipts'] == 200000
    receipt.cancel(); invoice.reload()
    assert flt(invoice.outstanding_amount) == 600000 and row()['unposted_collection'] == 200000
    replacement = accounting.make_collection_payment(scenario['delivery'], cash)
    assert replacement != receipt_name
    frappe.get_doc('Payment Entry', replacement).submit()
    rest = direct_payment(400000)
    invoice.reload(); assert flt(invoice.outstanding_amount) == 0
    rest.cancel(); invoice.reload(); assert flt(invoice.outstanding_amount) == 400000
    checks.append('Receipt deduplication, direct double collection blocked, cancellation restores debt')
    log = frappe.get_doc(dict(doctype='Vehicle Log', license_plate=trip.vehicle,
        employee=frappe.db.get_value('Driver', trip.driver, 'employee'), date=today(),
        odometer=frappe.db.get_value('Vehicle', trip.vehicle, 'last_odometer'),
        custom_delivery_trip=trip.name, custom_expense_type='Road Toll', custom_expense_amount=100000,
        custom_expense_note='Phí cầu đường chuyến vận chuyển bao bì', custom_approval_status='Draft')).insert()
    log.flags.dp_vehicle_log_transition = 'approve'
    log.flags.dp_vehicle_log_approval = True
    log.custom_approval_status = 'Approved'
    log.submit()
    journal = accounting.make_expense_entry(log.name, company.default_expense_account, cash, company.cost_center)
    assert accounting.make_expense_entry(log.name, company.default_expense_account, cash, company.cost_center) == journal
    entry = frappe.get_doc('Journal Entry', journal); entry.submit()
    result = row()
    assert result['posted_cost'] == result['approved_cost'] == 100000
    assert result['unposted_cost'] == 0 and result['margin'] == result['revenue'] - 100000
    reject(lambda: accounting.guard_source_cancel(log))
    entry.cancel()
    assert row()['posted_cost'] == 0 and row()['unposted_cost'] == 100000
    for dt, voucher in [('Sales Invoice', name), ('Payment Entry', replacement)]:
        balance = frappe.db.sql('''SELECT SUM(debit-credit) FROM `tabGL Entry`
            WHERE voucher_type=%s AND voucher_no=%s AND is_cancelled=0''', (dt, voucher))[0][0]
        assert abs(flt(balance)) < .000001
    checks.append('Approved expense posts balanced GL; cancel reverses cost; report matches ledger')
    return dict(checks=checks, transport_checks=scenario['checks'], retained=False)


if __name__ == '__main__':
    frappe.init(site='logistics-v16.localhost', sites_path='/home/frappe/frappe-bench/sites')
    frappe.connect()
    try:
        print(json.dumps(run(), ensure_ascii=False, default=str))
    finally:
        frappe.db.rollback()
        frappe.destroy()
