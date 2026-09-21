import frappe
from frappe.model.document import Document
from frappe.utils import flt

class DeliveryConfirmation(Document):
    def validate(self):
        self.validate_trip_and_stop()
        self.validate_items()

    def validate_trip_and_stop(self):
        trip = frappe.get_doc('Delivery Trip', self.delivery_trip)
        stop_names = [s.name for s in trip.delivery_stops]
        if self.delivery_stop not in stop_names:
            frappe.throw('Điểm giao không thuộc chuyến đã chọn.', title='DP_STOP_MISMATCH')

    def validate_items(self):
        for row in self.items:
            for f in ('allocated_qty', 'received_qty', 'returned_qty', 'pending_qty'):
                if flt(row.get(f)) < 0:
                    frappe.throw(f'{f} không được âm (dòng {row.idx}).', title='DP_NEGATIVE_QTY')

            total = flt(row.received_qty) + flt(row.returned_qty) + flt(row.pending_qty)
            if abs(total - flt(row.allocated_qty)) > 0.0001:
                frappe.throw(
                    f'Dòng {row.idx}: thực nhận + trả lại + còn chờ phải bằng số lượng phân giao.',
                    title='DP_QTY_MISMATCH')

            # Chặn cộng dồn vượt số lượng phân giao qua nhiều lần xác nhận
            already_confirmed = frappe.db.sql('''
                select coalesce(sum(dci.received_qty + dci.returned_qty), 0)
                from `tabDelivery Confirmation Item` dci
                join `tabDelivery Confirmation` dc on dc.name = dci.parent
                where dci.delivery_note_detail = %s
                  and dc.docstatus = 1
                  and dc.name != %s
            ''', (row.delivery_note_detail, self.name or ''))[0][0]

            if flt(already_confirmed) + flt(row.received_qty) + flt(row.returned_qty) > flt(row.allocated_qty) + 0.0001:
                frappe.throw(
                    f'Dòng {row.idx}: tổng các lần xác nhận vượt số lượng đã phân giao.',
                    title='DP_OVER_CONFIRM')
