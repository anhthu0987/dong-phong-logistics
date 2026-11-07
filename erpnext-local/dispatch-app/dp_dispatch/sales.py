import frappe


def prevent_unaccepting_quotation_with_order(doc, method=None):
	"""Keep an accepted quotation accepted while an active delivery order uses it."""
	if doc.custom_customer_accepted:
		return

	previous_value = frappe.db.get_value("Quotation", doc.name, "custom_customer_accepted")
	if not previous_value:
		return

	active_order = frappe.db.get_value(
		"Delivery Order",
		{"quotation": doc.name, "docstatus": ["!=", 2]},
		"name",
	)
	if active_order:
		frappe.throw(
			f"Không thể bỏ xác nhận đồng ý: báo giá này đã tạo đơn vận chuyển {active_order}. "
			"Hãy hủy đơn theo đúng quy trình trước nếu cần thay đổi trạng thái báo giá."
		)
