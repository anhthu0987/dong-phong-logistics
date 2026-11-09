"""Run offline: python -m unittest discover -s tests -p test_accounting.py."""
import importlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dp_dispatch.accounting_rules import amount, check_collection, collection_status, collection_required

class D(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__

class ValidationError(Exception):
    pass

class PermissionError(Exception):
    pass


def throw(message, exception=ValidationError):
    raise exception(message)

fake = types.ModuleType('frappe')
fake.whitelist = lambda *a, **k: lambda fn: fn
fake.throw = throw
fake.PermissionError = PermissionError
fake.session = D(user='Administrator')
fake.get_roles = lambda: []
fake.db = D(get_value=lambda *a, **k: None)
fake.get_cached_value = lambda *a: 'VND'
utils = types.ModuleType('frappe.utils')
utils.flt = lambda x, *a: float(x or 0)
utils.today = lambda: '2026-11-09'
with patch.dict(sys.modules, {'frappe': fake, 'frappe.utils': utils}):
    accounting = importlib.import_module('dp_dispatch.accounting')


def doc(**kwargs):
    return D(get_doc_before_save=lambda: None, **kwargs)


class CollectionTests(unittest.TestCase):
    def test_credit_may_finish_unpaid_or_partially_paid(self):
        self.assertFalse(collection_required({'custom_payment_policy': 'Credit'}))
        self.assertEqual(check_collection(600000, 0), 'Unpaid')
        self.assertEqual(check_collection(600000, 200000), 'Partially Paid')

    def test_existing_orders_still_collect_in_full(self):
        self.assertTrue(collection_required({}))
        with self.assertRaises(ValueError):
            check_collection(600000, 200000, required=True)
        self.assertEqual(check_collection(600000, 600000, True), 'Paid')

    def test_invalid_amounts_and_overcollection(self):
        for value in ['NaN', 'Infinity', '-1', 'bad']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                amount(value)
        with self.assertRaises(ValueError):
            collection_status(600000, 600001)
        self.assertEqual(collection_status(0, 0), 'Not Required')

    def test_float_rounding_does_not_reject_equal_amounts(self):
        self.assertEqual(collection_status(.3, .1 + .2), 'Paid')


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.source = D(name='C1', docstatus=1, shipping_fee_collected=200000,
                        delivery_order='O1', delivery_trip='T1')
        self.invoice = D(name='I1', docstatus=1, is_return=0, custom_delivery_order='O1',
                         custom_delivery_trip='T1', customer='Customer', company='Company',
                         debit_to='Receivable', currency='VND')
        self.payment = doc(doctype='Payment Entry', name='P1', custom_delivery_confirmation='C1',
                           payment_type='Receive', party_type='Customer', party='Customer', company='Company',
                           paid_from='Receivable', paid_to='Cash', paid_amount=200000, received_amount=200000,
                           paid_from_account_currency='VND', source_exchange_rate=1, target_exchange_rate=1,
                           deductions=[], taxes=[], references=[D(reference_doctype='Sales Invoice',
                           reference_name='I1', allocated_amount=200000)])
        self.patches = [patch.object(accounting, 'lock_source', side_effect=lambda dt, name: self.source if dt == 'Delivery Confirmation' else self.invoice),
                        patch.object(accounting, 'existing', return_value=None),
                        patch.object(accounting, 'account_details', return_value=D(account_type='Cash'))]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def test_valid_partial_collection_posts_exact_source_amount(self):
        accounting.validate_payment(self.payment)

    def test_mismatched_trip_customer_amount_and_canceled_source_rejected(self):
        changes = [(self.invoice, 'custom_delivery_trip', 'T2'), (self.payment, 'party', 'Other'),
                   (self.payment, 'received_amount', 199999), (self.source, 'docstatus', 2),
                   (self.payment, 'payment_type', 'Pay')]
        for target, key, value in changes:
            original = target[key]
            target[key] = value
            with self.subTest(key=key), self.assertRaises(ValidationError):
                accounting.validate_payment(self.payment)
            target[key] = original

    def test_duplicate_source_rejected_even_for_drafts(self):
        with patch.object(accounting, 'existing', return_value='P0'), self.assertRaises(ValidationError):
            accounting.validate_payment(self.payment)

    def test_driver_cannot_post_or_query_accounting(self):
        with patch.object(fake, 'session', D(user='driver')), self.assertRaises(PermissionError):
            accounting.validate_payment(self.payment)

    def test_cannot_unlink_source_to_bypass_validation(self):
        self.payment.get_doc_before_save = lambda: D(custom_delivery_confirmation='C1')
        self.payment.custom_delivery_confirmation = None
        with self.assertRaises(ValidationError):
            accounting.validate_payment(self.payment)

    def test_no_direct_receipt_while_driver_cash_is_unposted(self):
        self.payment.custom_delivery_confirmation = None
        with patch.object(fake, 'get_doc', return_value=self.invoice, create=True), \
                patch.object(accounting, 'unposted_collection', return_value=200000), self.assertRaises(ValidationError):
            accounting.validate_payment(self.payment)

    def test_direct_receipt_allowed_after_collections_are_posted(self):
        self.payment.custom_delivery_confirmation = None
        with patch.object(fake, 'get_doc', return_value=self.invoice, create=True), \
                patch.object(accounting, 'unposted_collection', return_value=0):
            accounting.validate_payment(self.payment)

    def test_cancel_source_blocked_until_accounting_document_canceled(self):
        with patch.object(accounting, 'existing', return_value='I1'), self.assertRaises(ValidationError):
            accounting.guard_source_cancel(D(doctype='Delivery Order', name='O1'))
        accounting.guard_source_cancel(D(doctype='Delivery Order', name='O1'))

    def test_invoice_total_customer_and_duplicate_guards(self):
        order = D(name='O1', customer='Customer', shipping_fee=600000)
        quote = D(company='Company', currency='VND')
        inv = doc(doctype='Sales Invoice', name='I1', custom_delivery_order='O1', custom_delivery_trip='T1',
                  is_return=0, company='Company', customer='Customer', currency='VND', grand_total=600000,
                  conversion_rate=1, update_stock=0, is_pos=0, disable_rounded_total=1)
        with patch.object(accounting, 'source_order', return_value=(order, D(name='T1'), quote)):
            accounting.validate_invoice(inv)
            inv.grand_total = 599999
            with self.assertRaises(ValidationError):
                accounting.validate_invoice(inv)
            inv.grand_total = 600000
            inv.customer = 'Other'
            with self.assertRaises(ValidationError):
                accounting.validate_invoice(inv)

    def test_expense_amount_approval_and_duplicate_claim_guards(self):
        log = D(name='L1', docstatus=1, custom_approval_status='Approved', custom_delivery_trip='T1',
                custom_expense_amount=100000, license_plate='Truck')
        trip = D(name='T1', docstatus=1, company='Company', vehicle='Truck')
        entry = doc(doctype='Journal Entry', name='J1', custom_vehicle_log='L1', custom_delivery_trip='T1',
                    company='Company', multi_currency=0, accounts=[
                    D(account='Expense', debit_in_account_currency=100000, credit_in_account_currency=0,
                      cost_center='Cost Center', exchange_rate=1),
                    D(account='Cash', debit_in_account_currency=0, credit_in_account_currency=100000, exchange_rate=1)])
        with patch.object(accounting, 'lock_source', return_value=log), \
             patch.object(fake, 'get_doc', return_value=trip, create=True), \
             patch.object(accounting, 'account_details', side_effect=lambda n,*_: D(root_type='Expense' if n=='Expense' else 'Asset', account_type='Cash' if n=='Cash' else '')), \
             patch.object(fake, 'db', D(get_value=lambda dt, name, field: 'Company' if field=='company' else 0)):
            accounting.validate_expense_entry(entry)
            log.custom_approval_status = 'Pending Review'
            with self.assertRaises(ValidationError):
                accounting.validate_expense_entry(entry)
            log.custom_approval_status = 'Approved'
            entry.accounts[0].debit_in_account_currency = 99999
            with self.assertRaises(ValidationError):
                accounting.validate_expense_entry(entry)
            entry.accounts[0].debit_in_account_currency = 100000
            with patch.object(accounting, 'existing', side_effect=lambda dt,*args,**kwargs: 'EC1' if dt=='Expense Claim' else None), self.assertRaises(ValidationError):
                accounting.validate_expense_entry(entry)


if __name__ == '__main__':
    unittest.main()
