"""Pickup/delivery planning and actual cargo ledger, persisted in MariaDB via Frappe."""
import math
from dp_dispatch.accounting_rules import collection_status

import frappe
from frappe.utils import flt, get_datetime, add_to_date

MODE = 'Pickup and Delivery'
EPS = 0.000001


def install_schema():
    from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
    def field(name, label, kind, **options):
        return dict(fieldname=name, label=label, fieldtype=kind, **options)
    order_fields = [field('transport_windows', 'Khung giờ lấy và giao hàng', 'Section Break', insert_after='delivery_date'),
                    field('pickup_city', 'Tỉnh/Thành phố lấy hàng', 'Data', insert_after='pickup_address'),
                    field('pickup_address_link', 'Địa chỉ lấy hàng liên kết', 'Link', options='Address', read_only=1, hidden=1)]
    previous = 'transport_windows'
    for prefix, label in [('pickup', 'lấy hàng'), ('delivery', 'giao hàng')]:
        for suffix, caption, kind in [('window_start', 'Từ', 'Datetime'), ('window_end', 'Đến', 'Datetime'), ('service_minutes', 'Thời gian phục vụ (phút)', 'Float')]:
            name = prefix + '_' + suffix
            order_fields.append(field(name, caption + ' — ' + label, kind, insert_after=previous, non_negative=1))
            previous = name
    create_custom_fields({
        'Delivery Order': order_fields,
        'Delivery Trip': [
            field('custom_transport_mode', 'Quy trình vận chuyển', 'Select', options='Delivery Only\nPickup and Delivery', default='Delivery Only', insert_after='driver', description='Lấy và giao: kiểm tra thứ tự điểm, khung giờ và tải theo từng chặng.'),
            field('custom_onboard_weight_kg', 'Hàng thực tế trên xe (kg)', 'Float', read_only=1, allow_on_submit=1, insert_after='custom_planned_load_kg'),
            field('custom_onboard_quantity', 'Số lượng thực tế trên xe', 'Data', read_only=1, allow_on_submit=1, insert_after='custom_onboard_weight_kg'),
        ],
        'Delivery Stop': [
            field('custom_stop_type', 'Loại điểm', 'Select', options='Pickup\nDelivery\nReturn', default='Delivery', in_list_view=1, insert_after='custom_delivery_order'),
            field('custom_window_start', 'Khung giờ từ', 'Datetime', insert_after='custom_stop_type'),
            field('custom_window_end', 'Khung giờ đến', 'Datetime', insert_after='custom_window_start'),
            field('custom_planned_arrival', 'Đến dự kiến', 'Datetime', in_list_view=1, insert_after='custom_window_end'),
            field('custom_service_minutes', 'Phục vụ (phút)', 'Float', non_negative=1, insert_after='custom_planned_arrival'),
            field('custom_load_after_kg', 'Tải sau điểm (kg)', 'Float', read_only=1, insert_after='custom_service_minutes'),
            field('custom_delivery_state', 'Tiến độ giao', 'Select', options='Assigned\nIn Transit\nPicked Up\nDelivered\nPartial\nReturned\nException', default='Assigned', read_only=1, allow_on_submit=1, insert_after='custom_delivery_order'),
        ],
        'Delivery Confirmation': [
            field('operation', 'Thao tác tại điểm', 'Select', options='Pickup\nDelivery\nReturn', default='Delivery', read_only=1, in_list_view=1, insert_after='delivery_stop'),
            field('window_exception', 'Thực hiện ngoài khung giờ', 'Check', read_only=1, insert_after='received_at'),
        ],
        'Delivery Confirmation Item': [
            field('picked_up_qty', 'Số lượng đã lấy lên xe', 'Float', default=0, non_negative=1, in_list_view=1, insert_after='allocated_qty'),
            field('returned_to_sender_qty', 'Đã trả lại người gửi', 'Float', default=0, non_negative=1, in_list_view=1, insert_after='returned_qty'),
        ],
    }, update=True)


def fail(message):
    frappe.throw('[DP_TRANSPORT] ' + message)


def quantity(value):
    value = flt(value)
    if not math.isfinite(value) or value < 0:
        fail('Số lượng, khối lượng và thời gian phục vụ phải hữu hạn, không âm.')
    return value


def enabled(trip):
    return trip.get('custom_transport_mode') == MODE


def validate_order(doc, method=None):
    if (doc.get('custom_payment_policy') or 'Collect on Delivery') not in ('Collect on Delivery', 'Credit'):
        fail('Điều kiện thanh toán không hợp lệ.')
    if doc.get('custom_payment_policy') == 'Credit' and not doc.get('custom_payment_due_date'):
        fail('Đơn công nợ cần hạn thanh toán.')
    for prefix in ('pickup', 'delivery'):
        start, end = doc.get(prefix + '_window_start'), doc.get(prefix + '_window_end')
        if bool(start) != bool(end):
            fail('Nhập đầy đủ giờ bắt đầu và kết thúc khung giờ lấy/giao.')
        if start and get_datetime(end) < get_datetime(start):
            fail('Giờ kết thúc khung giờ không được trước giờ bắt đầu.')
        quantity(doc.get(prefix + '_service_minutes'))
    if doc.get('pickup_window_start') and doc.get('delivery_window_end'):
        earliest = add_to_date(get_datetime(doc.pickup_window_start), minutes=quantity(doc.get('pickup_service_minutes')))
        if earliest > get_datetime(doc.delivery_window_end):
            fail('Khung giờ giao không thể kết thúc trước khi lấy hàng xong.')


def plan_trip(trip, method=None):
    """One full order per trip, one pickup then one delivery, optional return stop."""
    old = trip.get_doc_before_save()
    if old and old.docstatus == 1:
        return  # Submitted route is immutable; execution updates use the actual ledger.
    orders = {}
    for name in sorted({s.get('custom_delivery_order') for s in trip.delivery_stops if s.get('custom_delivery_order')}):
        # Lock orders in deterministic order to serialize allocation across vehicles.
        frappe.db.sql('SELECT name FROM `tabDelivery Order` WHERE name=%s FOR UPDATE', name)
        orders[name] = frappe.get_doc('Delivery Order', name)
    phases, onboard, peak, totals = {}, 0, 0, {}
    previous_end = get_datetime(trip.departure_time) if trip.departure_time else None
    for stop in trip.delivery_stops:
        name = stop.get('custom_delivery_order')
        kind = stop.get('custom_stop_type')
        if not name or stop.get('delivery_note') or kind not in ('Pickup', 'Delivery', 'Return'):
            fail('Mỗi điểm phải có một đơn vận chuyển và loại Lấy hàng / Giao hàng / Trả người gửi.')
        order = orders[name]
        if order.docstatus != 1 or order.delivery_status in ('Delivered', 'Returned', 'Partial', 'Cancelled'):
            fail('Chỉ phân đơn đã Submit và chưa có kết quả giao cuối.')
        active = frappe.db.sql('''SELECT t.name FROM `tabDelivery Trip` t
            JOIN `tabDelivery Stop` s ON s.parent=t.name AND s.parenttype='Delivery Trip'
            WHERE s.custom_delivery_order=%s AND t.name!=%s AND t.docstatus=1
            AND t.status IN ('Scheduled','In Transit') LIMIT 1 FOR UPDATE''', (name, trip.name or ''))
        if active:
            fail('Đơn đã được phân cho chuyến ' + active[0][0])
        phase = phases.get(name)
        weight = sum(quantity(i.qty) * quantity(i.weight_kg) for i in order.items)
        if weight <= 0:
            fail('Hàng trên đơn phải có khối lượng lớn hơn 0.')
        if kind == 'Pickup':
            if phase:
                fail('Một đơn chỉ có một điểm lấy trên chuyến.')
            phases[name] = 'Pickup'
            onboard += weight
            for row in order.items:
                totals[row.uom or 'kiện'] = totals.get(row.uom or 'kiện', 0) + quantity(row.qty)
        elif kind == 'Delivery':
            if phase != 'Pickup':
                fail('Phải lấy hàng trước khi giao; mỗi đơn chỉ có một điểm giao.')
            phases[name] = 'Delivery'
            onboard -= weight
        else:
            if phase != 'Delivery':
                fail('Điểm trả người gửi phải sau điểm giao của đơn.')
            phases[name] = 'Return'
        prefix = 'pickup' if kind in ('Pickup', 'Return') else 'delivery'
        stop.customer = order.customer
        stop.address = order.get('pickup_address_link') if prefix == 'pickup' else order.shipping_address
        stop.customer_address = order.pickup_address if prefix == 'pickup' else order.delivery_address
        if not stop.address:
            fail('Đơn chưa có địa chỉ liên kết cho điểm lấy/giao. Cập nhật địa chỉ trước khi phân chuyến.')
        # Return timing is entered explicitly; pickup window no longer applies.
        if kind != 'Return':
            stop.custom_window_start = order.get(prefix + '_window_start')
            stop.custom_window_end = order.get(prefix + '_window_end')
            stop.custom_service_minutes = quantity(order.get(prefix + '_service_minutes'))
        if not stop.get('custom_window_start') or not stop.get('custom_window_end') or not stop.get('custom_planned_arrival'):
            fail('Mỗi điểm cần khung giờ và thời gian đến dự kiến trước khi lưu chuyến lấy/giao.')
        start, end, arrival = map(get_datetime, (stop.custom_window_start, stop.custom_window_end, stop.custom_planned_arrival))
        if end < start or arrival < start or arrival > end:
            fail('Giờ đến dự kiến phải nằm trong khung giờ của điểm dừng.')
        if previous_end and arrival < previous_end:
            fail('Thời gian các điểm phải theo thứ tự, bao gồm thời gian phục vụ tại điểm trước.')
        previous_end = add_to_date(arrival, minutes=quantity(stop.custom_service_minutes))
        if trip.get('custom_expected_end_time') and previous_end > get_datetime(trip.custom_expected_end_time):
            fail('Chuyến phải kết thúc sau khi phục vụ xong điểm cuối.')
        stop.custom_load_after_kg = max(0, onboard)
        peak = max(peak, onboard)
    if not phases or any(phase == 'Pickup' for phase in phases.values()):
        fail('Mỗi đơn cần đủ điểm lấy và điểm giao.')
    trip.custom_planned_load_kg = peak
    trip.custom_total_delivery_qty = ' + '.join(f'{qty:g} {unit}' for unit, qty in sorted(totals.items()))
    if trip.docstatus == 1 or method == 'before_submit':
        for name in orders:
            frappe.db.set_value('Delivery Order', name, 'delivery_status', 'Assigned', update_modified=False)


def ledger(trip, exclude=None):
    """Per-source-row on-board quantity; no mixing UOM or counting pickup as delivery."""
    balances = {}
    docs = frappe.get_all('Delivery Confirmation', filters={'delivery_trip': trip.name, 'docstatus': 1}, pluck='name')
    for name in docs:
        if name == exclude:
            continue
        confirmation = frappe.get_doc('Delivery Confirmation', name)
        for row in confirmation.items:
            ref = row.get('delivery_order_item_ref')
            delta = flt(row.get('picked_up_qty')) - flt(row.delivered_qty) - flt(row.get('returned_to_sender_qty'))
            balances[ref] = balances.get(ref, 0) + delta
    return balances


def source_items(trip, stop):
    order = frappe.get_doc('Delivery Order', stop.custom_delivery_order)
    balances = ledger(trip)
    return order, [{
        'delivery_order_item_ref': row.name, 'description': row.description,
        'item_code_display': row.item_code, 'uom': row.uom,
        'allocated_qty': row.qty if stop.custom_stop_type == 'Pickup' else max(0, balances.get(row.name, 0)),
    } for row in order.items]


def validate_confirmation(doc, trip):
    from dp_dispatch.completion import ensure_assigned
    ensure_assigned(trip)
    if trip.status != 'In Transit' or trip.get('custom_completed_at'):
        fail('Chỉ xác nhận lấy/giao cho chuyến đang vận chuyển.')
    stop = next((s for s in trip.delivery_stops if s.name == doc.delivery_stop), None)
    if not stop:
        fail('Điểm xác nhận không thuộc chuyến.')
    kind = stop.custom_stop_type
    if kind not in ('Pickup', 'Delivery', 'Return'):
        fail('Loại điểm không hợp lệ.')
    doc.operation = kind
    doc.delivery_order = stop.custom_delivery_order
    doc.delivery_note = None
    existing = frappe.db.exists('Delivery Confirmation', {'delivery_trip': trip.name, 'delivery_stop': stop.name, 'docstatus': 1, 'name': ['!=', doc.name or '']})
    if existing:
        fail('Điểm đã có xác nhận được Submit.')
    # All previous required stops must be confirmed, preventing reversal of actual route.
    for earlier in trip.delivery_stops:
        if earlier.name == stop.name:
            break
        if not frappe.db.exists('Delivery Confirmation', {'delivery_trip': trip.name, 'delivery_stop': earlier.name, 'docstatus': 1}):
            fail('Cần xác nhận các điểm trước theo thứ tự chuyến.')
    order, expected = source_items(trip, stop)
    sources = {r.name: r for r in order.items}
    amounts = {r['delivery_order_item_ref']: flt(r['allocated_qty']) for r in expected}
    if not doc.items:
        for row in expected:
            doc.append('items', dict(row, pending_qty=row['allocated_qty']))
    seen = set()
    balances = ledger(trip)
    for row in doc.items:
        ref = row.get('delivery_order_item_ref')
        if ref not in sources or ref in seen:
            fail('Mỗi dòng phải tham chiếu đúng một dòng hàng nguồn, không lặp.')
        seen.add(ref)
        source = sources[ref]
        allocated, picked, delivered, returned, unloaded, pending = [quantity(row.get(f)) for f in (
            'allocated_qty', 'picked_up_qty', 'delivered_qty', 'returned_qty', 'returned_to_sender_qty', 'pending_qty')]
        if abs(allocated - amounts[ref]) > EPS:
            fail('Lượng xử lý phải bằng lượng hàng nguồn/đang trên xe của điểm này.')
        if kind == 'Pickup':
            if delivered or returned or unloaded or abs(allocated - picked - pending) > EPS:
                fail('Điểm lấy: lượng phân phải bằng lượng đã lấy + còn chờ; không nhập lượng giao/trả.')
        elif kind == 'Delivery':
            if picked or unloaded or abs(allocated - delivered - returned - pending) > EPS:
                fail('Điểm giao: lượng trên xe phải bằng đã giao + cần trả người gửi + còn chờ.')
        elif picked or delivered or returned or abs(allocated - unloaded - pending) > EPS:
            fail('Điểm trả: lượng còn trên xe phải bằng đã trả người gửi + còn chờ.')
        if doc.docstatus == 1 and pending > EPS:
            fail('Cần xác định đủ kết quả hàng tại điểm trước khi Submit.')
        row.description, row.item_code_display, row.uom = source.description, source.item_code, source.uom
        balances[ref] = balances.get(ref, 0) + picked - delivered - unloaded
        if balances[ref] < -EPS:
            fail('Không được giao/trả vượt lượng đã lấy lên xe.')
    if seen != set(sources):
        fail('Xác nhận phải có đầy đủ các dòng hàng của đơn.')
    weight = 0
    for ref, qty in balances.items():
        weight += qty * flt(frappe.db.get_value('Delivery Order Item', ref, 'weight_kg'))
    capacity = flt(frappe.db.get_value('Vehicle', trip.vehicle, 'custom_payload_capacity_kg'))
    if weight > capacity + EPS:
        fail('Hàng thực tế trên xe vượt tải trọng; kiểm tra hàng chưa giao/trả trước khi lấy thêm.')
    if not doc.received_at:
        fail('Nhập thời điểm lấy/giao thực tế.')
    actual = get_datetime(doc.received_at)
    if actual < get_datetime(trip.custom_started_at):
        fail('Thời điểm xác nhận không được trước lúc bắt đầu chuyến.')
    from frappe.utils import now_datetime
    if actual > add_to_date(now_datetime(), minutes=5):
        fail('Không xác nhận hàng ở thời điểm tương lai.')
    previous_times = frappe.get_all('Delivery Confirmation', filters={'delivery_trip': trip.name, 'docstatus': 1}, pluck='received_at')
    if previous_times and actual < max(map(get_datetime, previous_times)):
        fail('Thời điểm thực tế phải theo thứ tự xác nhận.')
    doc.window_exception = int(actual < get_datetime(stop.custom_window_start) or actual > get_datetime(stop.custom_window_end))
    if doc.window_exception and not (doc.notes or '').strip():
        fail('Thực hiện ngoài khung giờ: ghi rõ lý do trong ghi chú.')
    doc.shipping_fee_due = flt(order.shipping_fee) if kind == 'Delivery' else 0
    fee = quantity(doc.get('shipping_fee_collected'))
    if kind != 'Delivery' and fee:
        fail('Cước chỉ thu tại điểm giao, không thu lặp tại điểm lấy/trả.')
    if kind == 'Delivery':
        from dp_dispatch.accounting_rules import check_collection, collection_required
        try:
            check_collection(doc.shipping_fee_due, fee, doc.docstatus == 1 and collection_required(order))
        except ValueError as error:
            fail(str(error))
    if fee and not doc.get('fee_collection_method'):
        fail('Chọn phương thức thu cước.')


def update_actual(trip):
    balances = ledger(trip)
    weight = sum(qty * flt(frappe.db.get_value('Delivery Order Item', ref, 'weight_kg')) for ref, qty in balances.items())
    units = {}
    for ref, qty in balances.items():
        unit = frappe.db.get_value('Delivery Order Item', ref, 'uom') or 'kiện'
        units[unit] = units.get(unit, 0) + qty
    frappe.db.set_value('Delivery Trip', trip.name, {
        'custom_onboard_weight_kg': max(0, weight),
        'custom_onboard_quantity': ' + '.join(f'{qty:g} {unit}' for unit, qty in sorted(units.items()) if qty > EPS) or '0',
    }, update_modified=False)


def on_submit_confirmation(doc, trip):
    from frappe.utils import now_datetime
    kind = doc.operation
    state = 'Picked Up' if kind == 'Pickup' else ('Returned' if kind == 'Return' else ('Partial' if any(flt(r.returned_qty) for r in doc.items) else 'Delivered'))
    # ERPNext automatically completes trips when every stop.visited is true.
    # Only the dispatcher approval sets visited; operational state is independent.
    frappe.db.set_value('Delivery Stop', doc.delivery_stop, 'custom_delivery_state', state, update_modified=False)
    frappe.db.set_value('Delivery Trip', trip.name, 'custom_completion_status', 'Open', update_modified=False)
    if kind == 'Delivery':
        frappe.db.set_value('Delivery Order', doc.delivery_order, {
            'delivery_status': state, 'fee_paid': doc.shipping_fee_collected,
            'fee_status': collection_status(doc.shipping_fee_due, doc.shipping_fee_collected),
        }, update_modified=False)
    elif kind == 'Pickup':
        frappe.db.set_value('Delivery Order', doc.delivery_order, 'delivery_status', 'In Transit', update_modified=False)
    elif kind == 'Return':
        delivered = frappe.db.sql('''SELECT COALESCE(SUM(i.delivered_qty),0)
            FROM `tabDelivery Confirmation Item` i JOIN `tabDelivery Confirmation` c ON c.name=i.parent
            WHERE c.delivery_order=%s AND c.delivery_trip=%s AND c.docstatus=1''', (doc.delivery_order, trip.name))[0][0]
        frappe.db.set_value('Delivery Order', doc.delivery_order, 'delivery_status', 'Partial' if flt(delivered) else 'Returned', update_modified=False)
    if doc.shipping_fee_collected:
        frappe.db.set_value('Delivery Confirmation', doc.name, {'fee_collected_by': frappe.session.user, 'fee_collected_at': now_datetime()}, update_modified=False)
    update_actual(trip)


def validate_complete(trip):
    if any(abs(qty) > EPS for qty in ledger(trip).values()):
        fail('Không thể hoàn tất khi vẫn còn hàng trên xe; phải giao hoặc trả người gửi.')


def before_cancel(doc, trip):
    later = [s.name for s in trip.delivery_stops if s.idx > next(s.idx for s in trip.delivery_stops if s.name == doc.delivery_stop)]
    if later and frappe.db.exists('Delivery Confirmation', {'delivery_trip': trip.name, 'delivery_stop': ['in', later], 'docstatus': 1}):
        fail('Phải hủy xác nhận ở các điểm sau trước khi hủy điểm này.')


def on_cancel(doc, trip):
    frappe.db.set_value('Delivery Stop', doc.delivery_stop, {'custom_delivery_state': 'Assigned', 'visited': 0}, update_modified=False)
    if doc.operation == 'Delivery':
        frappe.db.set_value('Delivery Order', doc.delivery_order, {'delivery_status': 'In Transit', 'fee_paid': 0, 'fee_status': 'Unpaid'}, update_modified=False)
    elif doc.operation == 'Pickup':
        frappe.db.set_value('Delivery Order', doc.delivery_order, 'delivery_status', 'Assigned', update_modified=False)
    elif doc.operation == 'Return':
        frappe.db.set_value('Delivery Order', doc.delivery_order, 'delivery_status', 'Partial', update_modified=False)
    frappe.db.set_value('Delivery Trip', trip.name, 'custom_completion_status', 'Open', update_modified=False)
    update_actual(trip)


def before_cancel_trip(doc, method=None):
    if enabled(doc) and frappe.db.exists('Delivery Confirmation', {'delivery_trip': doc.name, 'docstatus': 1}):
        fail('Hủy các xác nhận lấy/giao theo thứ tự ngược trước khi hủy chuyến.')


def on_cancel_trip(doc, method=None):
    if enabled(doc):
        for name in {s.custom_delivery_order for s in doc.delivery_stops}:
            frappe.db.set_value('Delivery Order', name, 'delivery_status', 'Pending Assignment', update_modified=False)


def before_cancel_order(doc, method=None):
    if frappe.db.sql('''SELECT t.name FROM `tabDelivery Trip` t JOIN `tabDelivery Stop` s ON s.parent=t.name
        WHERE s.custom_delivery_order=%s AND t.docstatus=1 LIMIT 1''', doc.name):
        fail('Đơn đã có chuyến được Submit; xử lý chuyến trước khi hủy đơn.')


@frappe.whitelist()
def order_stops(order_name):
    order = frappe.get_doc('Delivery Order', order_name)
    order.check_permission('read')
    if order.docstatus != 1:
        fail('Chọn đơn đã Submit.')
    return [dict(custom_delivery_order=order.name, custom_stop_type=kind, customer=order.customer,
                 address=order.get('pickup_address_link') if kind == 'Pickup' else order.shipping_address,
                 customer_address=order.pickup_address if kind == 'Pickup' else order.delivery_address,
                 custom_window_start=order.get(prefix + '_window_start'),
                 custom_window_end=order.get(prefix + '_window_end'),
                 custom_planned_arrival=order.get(prefix + '_window_start'),
                 custom_service_minutes=order.get(prefix + '_service_minutes'))
            for kind, prefix in [('Pickup', 'pickup'), ('Delivery', 'delivery')]]
