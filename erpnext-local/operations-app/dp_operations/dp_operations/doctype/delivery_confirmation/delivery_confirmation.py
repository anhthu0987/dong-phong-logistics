import frappe
from frappe import _
from frappe.model.document import Document

class DeliveryConfirmation(Document):
    def validate(self):
        self.validate_stop_in_trip()
        self.validate_quantities_and_source()
        self.check_duplicate_items()

    def validate_stop_in_trip(self):
        """1. Kiểm tra điểm dừng có thuộc chuyến đi đã chọn không"""
        if not self.delivery_trip or not self.delivery_stop:
            return
        
        stops = frappe.get_all(
            "Delivery Stop",
            filters={"parent": self.delivery_trip},
            pluck="name"
        )
        if self.delivery_stop not in stops:
            frappe.throw(_("DP_STOP_MISMATCH: Điểm giao không thuộc chuyến đã chọn."))

    def validate_quantities_and_source(self):
        """2. Kiểm tra số lượng âm, tính cân bằng và đối chiếu chứng từ nguồn"""
        if not self.items:
            frappe.throw(_("Vui lòng nhập ít nhất một dòng hàng."))

        for row in self.items:
            # Chặn số lượng âm
            if (row.received_qty or 0) < 0 or (row.returned_qty or 0) < 0 or (row.pending_qty or 0) < 0:
                frappe.throw(_("DP_NEGATIVE_QTY: Số lượng nhận, trả hoặc chờ không được âm."))

            # Bắt buộc cân bằng: phân giao = nhận + trả + chờ
            total = (row.received_qty or 0) + (row.returned_qty or 0) + (row.pending_qty or 0)
            if round(total, 4) != round((row.allocated_qty or 0), 4):
                frappe.throw(_(f"DP_QTY_MISMATCH: Dòng {row.idx} - Tổng nhận + trả + chờ ({total}) phải bằng phân giao ({row.allocated_qty})."))

            # Đối chiếu số lượng và đơn vị tính (UOM) với Delivery Note Item nguồn
            dn_item_id = getattr(row, 'delivery_note_item', None)
            if dn_item_id:
                dn_item = frappe.db.get_value(
                    "Delivery Note Item",
                    dn_item_id,
                    ["qty", "uom", "item_code"],
                    as_dict=True
                )
                if dn_item:
                    # Kiểm tra UOM trùng khớp
                    row_uom = getattr(row, 'uom', None)
                    if row_uom and row_uom != dn_item.uom:
                        frappe.throw(_(f"DP_UOM_MISMATCH: Đơn vị tính {row_uom} ở dòng {row.idx} không khớp với chứng từ nguồn ({dn_item.uom})."))
                    
                    # Chặn tự ý sửa tăng số lượng phân giao vượt quá phiếu xuất gốc
                    if round(row.allocated_qty, 4) > round(dn_item.qty, 4):
                        frappe.throw(_(f"DP_OVER_ALLOCATED: Số phân giao ({row.allocated_qty}) vượt quá số lượng trên phiếu xuất kho ({dn_item.qty})."))

    def check_duplicate_items(self):
        """3. Chặn lọt dòng hàng trùng trong cùng một xác nhận"""
        seen = set()
        for row in self.items:
            key = getattr(row, 'delivery_note_item', None) or row.item_code
            if key in seen:
                frappe.throw(_(f"DP_DUPLICATE_ITEM: Dòng {row.idx} bị trùng mặt hàng hoặc mã chứng từ nguồn ({key})."))
            seen.add(key)