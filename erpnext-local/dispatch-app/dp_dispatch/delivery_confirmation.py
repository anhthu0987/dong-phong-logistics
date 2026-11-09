"""Server validation and rollups for stock-free delivery orders and legacy ERPNext notes."""
import frappe
from frappe.utils import flt, now_datetime


@frappe.whitelist()
def get_trip_stops(delivery_trip):
	"""List the caller's stops on a trip for selecting a confirmation target."""
	trip = frappe.get_doc("Delivery Trip", delivery_trip)
	trip.check_permission("read")
	from dp_dispatch.completion import ensure_assigned
	ensure_assigned(trip)
	return [{
		"value": row.name,
		"label": f"{row.idx}. { {'Pickup': 'Lấy hàng', 'Delivery': 'Giao hàng', 'Return': 'Trả người gửi'}.get(row.get('custom_stop_type'), 'Giao hàng')} — {row.customer or 'Khách chưa xác định'} — {row.customer_address or row.address or 'Chưa có địa chỉ'} ({row.get('custom_delivery_order') or row.get('delivery_note') or 'Chưa gắn đơn'})",
	} for row in trip.delivery_stops]


@frappe.whitelist()
def get_stop_details(delivery_trip, delivery_stop):
	"""Return source details for a stop after verifying the caller's trip access."""
	trip = frappe.get_doc("Delivery Trip", delivery_trip)
	trip.check_permission("read")
	from dp_dispatch.completion import ensure_assigned
	ensure_assigned(trip)
	stop = next((row for row in trip.delivery_stops if row.name == delivery_stop), None)
	if not stop:
		frappe.throw("Điểm giao không thuộc chuyến đã chọn.", frappe.PermissionError)
	order_name = stop.get("custom_delivery_order")
	items = []
	from dp_dispatch import transport
	if transport.enabled(trip):
		order, items = transport.source_items(trip, stop)
		return {'delivery_order': order.name, 'items': items, 'operation': stop.custom_stop_type,
		        'shipping_fee': order.shipping_fee if stop.custom_stop_type == 'Delivery' else 0}
	if order_name:
		order = frappe.get_doc("Delivery Order", order_name)
		for row in order.items:
			items.append({
				"delivery_order_item_ref": row.name,
				"item_code_display": row.item_code,
				"description": row.description or row.item_code,
				"uom": row.uom or "kiện",
				"allocated_qty": row.qty,
			})
	else:
		note_name = stop.get("delivery_note")
		if note_name:
			note = frappe.get_doc("Delivery Note", note_name)
			for row in note.items:
				items.append({
					"delivery_note_item_ref": row.name,
					"item_code_display": row.item_code,
					"description": row.item_name or row.item_code,
					"uom": row.uom or row.stock_uom,
					"allocated_qty": row.qty,
				})
	return {
		"delivery_order": order_name,
		"delivery_note": stop.get("delivery_note"),
		"shipping_fee": frappe.db.get_value("Delivery Order", order_name, "shipping_fee") if order_name else 0,
		"items": items,
	}


def fail(code, message):
	frappe.throw(f"[{code}] {message}")


def validate_confirmation(doc, method=None):
	frappe.db.sql("SELECT name FROM `tabDelivery Trip` WHERE name=%s FOR UPDATE", doc.delivery_trip)
	trip = frappe.get_doc("Delivery Trip", doc.delivery_trip)
	from dp_dispatch import transport
	if transport.enabled(trip):
		return transport.validate_confirmation(doc, trip)
	if trip.docstatus != 1:
		fail("DPOD_TRIP", "Chỉ xác nhận giao nhận cho chuyến đã được điều phối và Submit.")
	if trip.get("custom_completed_at"):
		fail("DPOD_CLOSED", "Chuyến đã được quản trị viên duyệt hoàn tất.")
	if trip.get("custom_completion_status") == "Approved":
		fail("DPOD_CLOSED", "Chuyến đã được quản trị viên duyệt hoàn tất.")
	# A common driver workflow is one confirmation per stop. Resolve the stop on
	# the server when the browser could not load its selector (for example, due
	# to a stale client script). Never guess when the trip has multiple stops.
	if not doc.delivery_stop:
		if len(trip.delivery_stops) == 1:
			doc.delivery_stop = trip.delivery_stops[0].name
		else:
			fail("DPOD_STOP_REQUIRED", "Chuyến có nhiều điểm giao. Hãy chọn đúng điểm giao trong danh sách trên phiếu xác nhận.")
	stop = next((row for row in trip.delivery_stops if row.name == doc.delivery_stop), None)
	if not stop:
		fail("DPOD_STOP", "Điểm giao không thuộc chuyến đã chọn.")
	order_name = stop.get("custom_delivery_order")
	note_name = stop.get("delivery_note")
	if bool(order_name) == bool(note_name):
		fail("DPOD_SOURCE", "Mỗi điểm dừng cần gắn đúng một đơn giao hoặc một Delivery Note.")
	if doc.get("delivery_order") and doc.delivery_order != order_name:
		fail("DPOD_ORDER_MISMATCH", "Đơn giao phải trùng đơn được phân tại điểm dừng.")
	if doc.get("delivery_note") and doc.delivery_note != note_name:
		fail("DPOD_NOTE_MISMATCH", "Delivery Note phải trùng phiếu gắn tại điểm dừng.")
	doc.delivery_order = order_name
	doc.delivery_note = note_name
	if order_name:
		order = frappe.get_doc("Delivery Order", order_name)
		if order.docstatus != 1:
			fail("DPOD_ORDER_STATUS", "Đơn giao phải được xác nhận trước khi đưa lên chuyến.")
		order_rows = {row.name: row for row in order.items}
		source_doctype = "Delivery Order Item"
		qty_field = "qty"
	else:
		order = None
		note = frappe.get_doc("Delivery Note", note_name)
		if note.docstatus != 1 or note.is_return:
			fail("DPOD_NOTE_STATUS", "Delivery Note nguồn phải là phiếu xuất đã Submit, không phải phiếu trả hàng.")
		order_rows = {row.name: row for row in note.items}
		source_doctype = "Delivery Note Item"
		qty_field = "qty"

	if doc.docstatus == 1 or method == "before_submit":
		duplicate = frappe.db.exists("Delivery Confirmation", {
			"delivery_trip": doc.delivery_trip, "delivery_stop": doc.delivery_stop,
			"docstatus": 1, "name": ["!=", doc.name or ""]})
		if duplicate:
			fail("DPOD_DUPLICATE", "Điểm giao đã có xác nhận được Submit.")
	if not doc.items:
		# Recover the draft form when client-side item loading failed. The driver
		# can then enter actual delivered/returned/pending quantities before submit.
		for source in order_rows.values():
			qty = flt(source.get(qty_field), 6)
			values = {
				"allocated_qty": qty,
				"delivered_qty": 0,
				"returned_qty": 0,
				"pending_qty": qty,
				"uom": source.get("uom") or ("kiện" if order else source.get("stock_uom")),
			}
			if order:
				values.update({
					"delivery_order_item_ref": source.name,
					"description": source.description or source.item_code or "",
					"item_code_display": source.item_code,
				})
			else:
				values.update({
					"delivery_note_item_ref": source.name,
					"description": source.item_name or source.item_code or "",
					"item_code_display": source.item_code,
				})
			doc.append("items", values)
	if not doc.items:
		fail("DPOD_ITEMS", "Đơn nguồn chưa có dòng hàng nào để xác nhận.")

	allocated_in_doc = {}
	for row in doc.items:
		ref = row.get("delivery_order_item_ref") if order else row.get("delivery_note_item_ref")
		wrong_ref = row.get("delivery_note_item_ref") if order else row.get("delivery_order_item_ref")
		if not ref or wrong_ref:
			fail("DPOD_ITEM_SOURCE", "Mỗi dòng xác nhận phải tham chiếu một dòng hàng thuộc đúng loại đơn nguồn.")
		source = order_rows.get(ref)
		if not source:
			fail("DPOD_SOURCE", "Dòng hàng không thuộc đơn giao/phiếu xuất của điểm dừng này.")
		allocated = flt(row.allocated_qty, 6)
		delivered = flt(row.delivered_qty, 6)
		returned = flt(row.returned_qty, 6)
		pending = flt(row.pending_qty, 6)
		if min(allocated, delivered, returned, pending) < 0:
			fail("DPOD_NEGATIVE", "Số lượng phân giao, nhận, trả và chờ không được âm.")
		if abs(allocated - delivered - returned - pending) > 0.000001:
			fail("DPOD_BALANCE", "Phân giao phải bằng thực nhận + trả lại + còn chờ.")
		if method == "before_submit" and pending > 0:
			fail("DPOD_PENDING", "Hãy giữ phiếu ở Draft đến khi đã xác định kết quả cuối cho toàn bộ hàng của điểm giao.")
		if allocated <= 0 or allocated - flt(source.get(qty_field), 6) > 0.000001:
			fail("DPOD_OVER_SOURCE", "Lượng phân giao phải lớn hơn 0 và không vượt số lượng trên đơn nguồn.")
		if order:
			row.description = source.description or (source.item_code or "")
			row.item_code_display = source.item_code
			row.uom = source.uom or "kiện"
		else:
			row.item_code_display = source.item_code
			row.description = source.item_name or source.item_code or ""
			row.uom = source.uom or source.stock_uom
		allocated_in_doc[ref] = allocated_in_doc.get(ref, 0) + allocated
		used = frappe.db.sql(f"""SELECT COALESCE(SUM(item.allocated_qty), 0)
			FROM `tabDelivery Confirmation Item` item
			INNER JOIN `tabDelivery Confirmation` parent ON parent.name=item.parent
			WHERE item.{"delivery_order_item_ref" if order else "delivery_note_item_ref"}=%s
			AND parent.docstatus=1 AND parent.name!=%s""", (ref, doc.name or ""))[0][0]
		if flt(used, 6) + allocated_in_doc[ref] - flt(source.get(qty_field), 6) > 0.000001:
			fail("DPOD_CUMULATIVE", "Tổng lượng phân giao vượt số lượng trên đơn nguồn.")

	doc.shipping_fee_due = flt(order.shipping_fee) if order else 0
	fee = flt(doc.get("shipping_fee_collected"))
	if fee < 0:
		fail("DPOD_FEE", "Phí thu không được âm.")
	if order:
		previous_paid = flt(order.fee_paid)
		if previous_paid + fee - flt(order.shipping_fee) > 0.000001:
			fail("DPOD_FEE_OVER", "Tổng phí đã thu vượt phí vận chuyển của đơn.")
		from dp_dispatch.accounting_rules import collection_required
		if method == "before_submit" and collection_required(order) and previous_paid + fee + 0.000001 < flt(order.shipping_fee):
			fail("DPOD_FEE_UNPAID", "Cần thu đủ phí vận chuyển của đơn trước khi Submit xác nhận giao hàng.")
	if fee and not doc.get("fee_collection_method"):
		fail("DPOD_FEE_METHOD", "Chọn phương thức khi có thu phí vận chuyển.")


def _rollup_order(order_name):
	order = frappe.get_doc("Delivery Order", order_name)
	confirmations = frappe.get_all("Delivery Confirmation", filters={"delivery_order": order_name, "docstatus": 1}, pluck="name")
	paid = 0
	for name in confirmations:
		paid += flt(frappe.db.get_value("Delivery Confirmation", name, "shipping_fee_collected"))
	paid = min(paid, flt(order.shipping_fee))
	status = "Not Required" if flt(order.shipping_fee) <= 0 else ("Paid" if paid >= flt(order.shipping_fee) else ("Partially Paid" if paid else "Unpaid"))
	frappe.db.set_value("Delivery Order", order_name, {"fee_paid": paid, "fee_status": status}, update_modified=False)

	results = []
	for name in confirmations:
		for item in frappe.get_all("Delivery Confirmation Item", filters={"parent": name}, fields=["delivered_qty", "returned_qty", "pending_qty"]):
			results.append(item)
	if results:
		delivered = sum(flt(row.delivered_qty) for row in results)
		returned = sum(flt(row.returned_qty) for row in results)
		pending = sum(flt(row.pending_qty) for row in results)
		state = ("Partial" if delivered or returned else "In Transit") if pending else ("Delivered" if delivered and not returned else ("Returned" if returned and not delivered else "Partial"))
		frappe.db.set_value("Delivery Order", order_name, "delivery_status", state, update_modified=False)


def on_submit_confirmation(doc, method=None):
	from dp_dispatch import transport
	trip = frappe.get_doc('Delivery Trip', doc.delivery_trip)
	if transport.enabled(trip):
		return transport.on_submit_confirmation(doc, trip)
	if doc.delivery_order:
		_rollup_order(doc.delivery_order)
	stop = frappe.get_doc("Delivery Stop", doc.delivery_stop)
	allocated = sum(flt(row.allocated_qty) for row in doc.items)
	delivered = sum(flt(row.delivered_qty) for row in doc.items)
	returned = sum(flt(row.returned_qty) for row in doc.items)
	pending = sum(flt(row.pending_qty) for row in doc.items)
	state = "In Transit" if pending else ("Delivered" if delivered and not returned else ("Returned" if returned and not delivered else "Partial"))
	frappe.db.set_value("Delivery Stop", stop.name, "custom_delivery_state", state, update_modified=False)
	frappe.db.set_value("Delivery Trip", doc.delivery_trip, "custom_completion_status", "Open", update_modified=False)
	if flt(doc.get("shipping_fee_collected")) > 0:
		frappe.db.set_value("Delivery Confirmation", doc.name, {
			"fee_collected_by": frappe.session.user,
			"fee_collected_at": now_datetime(),
		}, update_modified=False)


def on_cancel_confirmation(doc, method=None):
	from dp_dispatch import transport
	trip = frappe.get_doc('Delivery Trip', doc.delivery_trip)
	if transport.enabled(trip):
		return transport.on_cancel(doc, trip)
	if doc.delivery_order:
		_rollup_order(doc.delivery_order)
		trip = frappe.get_doc("Delivery Trip", doc.delivery_trip)
		frappe.db.set_value("Delivery Order", doc.delivery_order,
			"delivery_status", "In Transit" if trip.get("custom_started_at") else "Assigned", update_modified=False)
	frappe.db.set_value("Delivery Stop", doc.delivery_stop, "custom_delivery_state", "Assigned", update_modified=False)
	frappe.db.set_value("Delivery Trip", doc.delivery_trip, "custom_completion_status", "Open", update_modified=False)


def before_cancel_confirmation(doc, method=None):
	frappe.db.sql("SELECT name FROM `tabDelivery Trip` WHERE name=%s FOR UPDATE", doc.delivery_trip)
	if frappe.db.get_value("Delivery Trip", doc.delivery_trip, "custom_completed_at"):
		frappe.throw("Không hủy xác nhận sau khi Admin đã duyệt hoàn tất chuyến.")
	from dp_dispatch import transport
	trip = frappe.get_doc('Delivery Trip', doc.delivery_trip)
	if transport.enabled(trip):
		transport.before_cancel(doc, trip)


def on_submit_order(doc, method=None):
	if not doc.get('pickup_address_link'):
		address = frappe.get_doc({
			'doctype': 'Address', 'address_title': f'Lấy hàng {doc.name}', 'address_type': 'Shipping',
			'address_line1': doc.pickup_address, 'city': doc.get('pickup_city') or doc.delivery_city,
			'country': doc.delivery_country or 'Vietnam',
			'links': [{'link_doctype': 'Customer', 'link_name': doc.customer}],
		}).insert(ignore_permissions=True)
		frappe.db.set_value('Delivery Order', doc.name, 'pickup_address_link', address.name, update_modified=False)
	if not doc.shipping_address:
		address = frappe.get_doc({
			"doctype": "Address",
			"address_title": f"Giao hàng {doc.name}",
			"address_type": "Shipping",
			"address_line1": doc.delivery_address,
			"city": doc.delivery_city,
			"country": doc.delivery_country or "Vietnam",
			"links": [{"link_doctype": "Customer", "link_name": doc.customer}],
		}).insert(ignore_permissions=True)
		frappe.db.set_value("Delivery Order", doc.name, "shipping_address", address.name, update_modified=False)
	frappe.db.set_value("Delivery Order", doc.name, "delivery_status", "Pending Assignment", update_modified=False)
