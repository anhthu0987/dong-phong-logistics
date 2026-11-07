"""Driver completion requests and dispatcher approval for Delivery Trip."""
import frappe
from frappe.utils import flt, now_datetime

from dp_dispatch.permissions import driver_for_user, is_driver


def lock_trip(name):
	frappe.db.sql("SELECT name FROM `tabDelivery Trip` WHERE name=%s FOR UPDATE", name)
	return frappe.get_doc("Delivery Trip", name)


def is_dispatcher():
	return frappe.session.user == "Administrator" or bool(set(frappe.get_roles()) & {"System Manager", "Fleet Manager"})


def save_action(doc, status_after_save=None):
	"""Save allowed operational fields, then update ERPNext's standard status.

	Delivery Trip is a submittable DocType and Frappe blocks changing its standard
	``status`` field through ``doc.save()`` after submission. The action endpoints
	validate the actor and the allowed state transition before calling this helper,
	so persist the status separately after the normal document save succeeds.
	"""
	previous = frappe.flags.get("dp_trip_action")
	frappe.flags.dp_trip_action = doc.name
	try:
		if status_after_save:
			doc.status = frappe.db.get_value("Delivery Trip", doc.name, "status")
		doc.save(ignore_permissions=True)
		if status_after_save:
			frappe.db.set_value("Delivery Trip", doc.name, "status", status_after_save, update_modified=True)
			doc.status = status_after_save
	finally:
		frappe.flags.dp_trip_action = previous


def ensure_assigned(doc, user=None):
	user = user or frappe.session.user
	if is_driver(user) and (not driver_for_user(user) or doc.driver != driver_for_user(user)):
		frappe.throw("Bạn chỉ được thao tác trên chuyến đã phân cho mình.", frappe.PermissionError)
	if not is_driver(user) and not is_dispatcher():
		frappe.throw("Chỉ tài xế được phân công hoặc điều phối viên mới thao tác được.", frappe.PermissionError)


def submitted_confirmations(trip, stop):
	return frappe.get_all("Delivery Confirmation", filters={
		"delivery_trip": trip.name, "delivery_stop": stop.name, "docstatus": 1,
	}, pluck="name")


def validate_all_stops(trip):
	if not trip.delivery_stops:
		frappe.throw("Chuyến chưa có điểm giao.")
	for stop in trip.delivery_stops:
		names = submitted_confirmations(trip, stop)
		if not names:
			frappe.throw(f"Điểm giao {stop.idx} chưa có xác nhận giao nhận đã Submit.")
		for name in names:
			confirmation = frappe.get_doc("Delivery Confirmation", name)
			if any(flt(row.pending_qty) > 0 for row in confirmation.items):
				frappe.throw(f"Điểm giao {stop.idx} còn hàng chờ xử lý.")
		if stop.get("custom_delivery_order"):
			order = frappe.get_doc("Delivery Order", stop.custom_delivery_order)
			paid = sum(flt(frappe.db.get_value("Delivery Confirmation", name, "shipping_fee_collected")) for name in names)
			if paid + 0.000001 < flt(order.shipping_fee):
				frappe.throw(f"Đơn {order.name} chưa thu đủ phí vận chuyển.")


@frappe.whitelist()
def get_stop_board(trip):
	doc = frappe.get_doc("Delivery Trip", trip)
	doc.check_permission("read")
	ensure_assigned(doc)
	board = []
	for stop in doc.delivery_stops:
		item_totals = {}
		order_name = stop.get("custom_delivery_order")
		if order_name:
			order = frappe.get_doc("Delivery Order", order_name)
			for item in order.items:
				unit = item.uom or "kiện"
				item_totals[unit] = item_totals.get(unit, 0) + flt(item.qty)
		names = submitted_confirmations(doc, stop)
		quantities = {"allocated": 0, "delivered": 0, "returned": 0, "pending": 0}
		for name in names:
			for row in frappe.get_all("Delivery Confirmation Item", filters={"parent": name}, fields=["allocated_qty", "delivered_qty", "returned_qty", "pending_qty"]):
				for field in quantities:
					quantities[field] += flt(row.get(field + "_qty"))
		board.append({
			"stop": stop.name, "customer": stop.customer, "address": stop.get("customer_address") or stop.get("address"),
			"order": order_name, "status": stop.get("custom_delivery_state") or "Assigned",
			"total": " + ".join(f"{qty:g} {unit}" for unit, qty in sorted(item_totals.items())),
			"quantities": quantities,
		})
	return board


@frappe.whitelist(methods=["POST"])
def start_trip(trip):
	doc = lock_trip(trip)
	ensure_assigned(doc)
	doc.check_permission("read")
	if doc.docstatus != 1 or doc.status != "Scheduled" or doc.get("custom_completed_at"):
		frappe.throw("Chỉ bắt đầu chuyến đã Submit ở trạng thái Scheduled.")
	if is_driver() and not doc.driver:
		frappe.throw("Chuyến chưa được gán tài xế.")
	doc.custom_started_at = now_datetime()
	doc.custom_started_by = frappe.session.user
	for stop in doc.delivery_stops:
		if stop.get("custom_delivery_order"):
			frappe.db.set_value("Delivery Order", stop.custom_delivery_order, "delivery_status", "In Transit", update_modified=False)
	save_action(doc, status_after_save="In Transit")
	doc.add_comment("Info", "Bắt đầu chuyến bởi " + frappe.session.user)
	return doc.status


@frappe.whitelist(methods=["POST"])
def request_completion(trip):
	doc = lock_trip(trip)
	ensure_assigned(doc)
	if doc.docstatus != 1 or doc.status == "Completed" or doc.get("custom_completed_at"):
		frappe.throw("Chuyến không ở trạng thái có thể yêu cầu hoàn tất.")
	if is_driver() and not doc.get("custom_started_at"):
		frappe.throw("Cần bắt đầu chuyến trước khi yêu cầu kết thúc.")
	validate_all_stops(doc)
	doc.custom_completion_status = "Requested"
	doc.custom_completion_requested_at = now_datetime()
	doc.custom_completion_requested_by = frappe.session.user
	doc.custom_completion_review_note = None
	save_action(doc)
	doc.add_comment("Info", "Tài xế yêu cầu duyệt hoàn tất chuyến.")
	return doc.custom_completion_status


@frappe.whitelist(methods=["POST"])
def approve_completion(trip, note=None):
	frappe.only_for("System Manager")
	doc = lock_trip(trip)
	if doc.docstatus != 1 or doc.get("custom_completion_status") != "Requested":
		frappe.throw("Chuyến chưa có yêu cầu hoàn tất đang chờ duyệt.")
	validate_all_stops(doc)
	for stop in doc.delivery_stops:
		stop.visited = 1
	doc.custom_completion_status = "Approved"
	doc.custom_completed_at = now_datetime()
	doc.custom_completed_by = frappe.session.user
	doc.custom_completion_review_note = note
	save_action(doc, status_after_save="Completed")
	doc.add_comment("Info", "Quản trị viên duyệt hoàn tất chuyến.")
	return doc.status


@frappe.whitelist(methods=["POST"])
def reject_completion(trip, note):
	frappe.only_for("System Manager")
	if not note:
		frappe.throw("Nhập lý do từ chối để tài xế biết cần xử lý gì.")
	doc = lock_trip(trip)
	if doc.get("custom_completion_status") != "Requested":
		frappe.throw("Chuyến chưa có yêu cầu hoàn tất đang chờ duyệt.")
	doc.custom_completion_status = "Rejected"
	doc.custom_completion_review_note = note
	save_action(doc)
	doc.add_comment("Info", "Từ chối hoàn tất chuyến: " + note)
	return doc.custom_completion_status
