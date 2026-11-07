import frappe
from frappe.model.document import Document
from frappe.utils import flt


class DeliveryOrder(Document):
	def validate(self):
		if not self.quotation and (self.is_new() or self.docstatus == 0):
			frappe.throw("Chỉ tạo đơn vận chuyển từ báo giá đã được khách xác nhận. Mở báo giá và dùng Tác vụ → Tạo đơn vận chuyển.")

		if self.quotation:
			quotation = frappe.db.get_value(
				"Quotation", self.quotation, ["docstatus", "quotation_to", "party_name", "custom_customer_accepted"], as_dict=True
			)
			if not quotation or quotation.docstatus != 1:
				frappe.throw("Chỉ được liên kết báo giá đã Submit với Delivery Order.")
			if quotation.quotation_to != "Customer" or quotation.party_name != self.customer:
				frappe.throw("Khách hàng trên Delivery Order phải trùng với khách hàng của báo giá.")
			if not quotation.custom_customer_accepted:
				frappe.throw("Chưa thể tạo đơn vận chuyển: hãy xác nhận khách đã đồng ý báo giá và đánh dấu ô xác nhận trên báo giá trước.")
			existing_order = frappe.db.get_value(
				"Delivery Order",
				{"quotation": self.quotation, "docstatus": ["!=", 2]},
				"name",
			)
			if existing_order and existing_order != self.name:
				frappe.throw(f"Báo giá này đã được dùng để tạo đơn vận chuyển {existing_order}.")

		if not self.items:
			frappe.throw("Đơn giao phải có ít nhất một kiện hàng.")
		totals = {}
		weight = 0
		for row in self.items:
			qty = flt(row.qty)
			unit_weight = flt(row.weight_kg)
			if qty <= 0:
				frappe.throw(f"Dòng {row.idx}: số lượng phải lớn hơn 0.")
			if unit_weight <= 0:
				frappe.throw(f"Dòng {row.idx}: nhập khối lượng mỗi đơn vị lớn hơn 0 để hệ thống kiểm tra tải trọng xe.")
			if not row.description and not row.item_code:
				frappe.throw(f"Dòng {row.idx}: nhập mô tả hàng hoặc chọn Item.")
			unit = row.uom or "kiện"
			totals[unit] = totals.get(unit, 0) + qty
			weight += qty * unit_weight
		self.total_quantity_display = " + ".join(
			f"{value:g} {unit}" for unit, value in sorted(totals.items())
		)
		self.total_weight_kg = weight
		self.shipping_fee = flt(self.shipping_fee)
		if self.shipping_fee < 0:
			frappe.throw("Phí vận chuyển không được âm.")
		if self.docstatus == 1 and not self.customer and not self.sender_name:
			frappe.throw("Cần thông tin khách hàng hoặc người gửi trước khi xác nhận đơn.")

	def after_insert(self):
		if self.quotation:
			frappe.db.set_value("Quotation", self.quotation, "delivery_order", self.name, update_modified=False)

	def on_cancel(self):
		self.clear_quotation_delivery_order_link()

	def on_trash(self):
		self.clear_quotation_delivery_order_link()

	def clear_quotation_delivery_order_link(self):
		if self.quotation and frappe.db.get_value("Quotation", self.quotation, "delivery_order") == self.name:
			frappe.db.set_value("Quotation", self.quotation, "delivery_order", None, update_modified=False)
