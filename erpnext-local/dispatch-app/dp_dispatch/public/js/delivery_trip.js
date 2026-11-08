frappe.provide('dp_gps');

dp_gps.load_leaflet = function () {
  const CSS = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
  const JS = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
  if (!document.querySelector('link[href="' + CSS + '"]')) {
    const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = CSS; document.head.appendChild(l);
  }
  return new Promise((resolve, reject) => {
    if (window.L) return resolve();
    const s = document.createElement('script'); s.src = JS; s.onload = resolve; s.onerror = reject;
    document.head.appendChild(s);
  });
};

dp_gps.show_trip_map = async function (frm) {
  try { await dp_gps.load_leaflet(); } catch (e) { return frappe.msgprint(__('Cannot load Leaflet')); }
  const esc = frappe.utils.escape_html;
  const stops = (frm.doc.delivery_stops || []).filter(s => s.lat && s.lng);
  const hasOrigin = frm.doc.custom_origin_lat && frm.doc.custom_origin_lng;
  const track = await frappe.db.get_list('GPS Log', {
    filters: { delivery_trip: frm.doc.name }, fields: ['latitude', 'longitude'],
    order_by: 'recorded_at asc', limit: 3000 });
  let veh = null;
  if (frm.doc.vehicle) {
    const r = await frappe.db.get_value('Vehicle', frm.doc.vehicle,
      ['custom_last_lat', 'custom_last_lng', 'custom_last_gps_time']);
    veh = r.message;
  }
  if (!stops.length && !track.length) return frappe.msgprint(__('Chuyến chưa có tọa độ GPS nào'));

  const d = new frappe.ui.Dialog({
    title: __('Bản đồ chuyến xe: {0}', [frm.doc.name]), size: 'extra-large',
    fields: [{ fieldtype: 'HTML', fieldname: 'map_html' }] });
  d.fields_dict.map_html.$wrapper.html(
    '<div id="dp-trip-map" style="height:60vh;min-height:360px;border-radius:8px"></div>' +
    '<div class="text-muted small" style="margin-top:6px">' +
    __('Nét đứt đỏ: lộ trình kế hoạch') + ' · ' + __('Xanh dương: vệt GPS') + ' · ' + __('Chấm xanh lá: vị trí xe mới nhất') +
    '</div>');
  d.show();

  setTimeout(() => {
    const map = L.map('dp-trip-map');
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      { maxZoom: 19, attribution: '&copy; OpenStreetMap contributors' }).addTo(map);
    const all = [];
    const o = hasOrigin ? [frm.doc.custom_origin_lat, frm.doc.custom_origin_lng] : null;
    const path = (o ? [o] : []).concat(stops.map(s => [s.lat, s.lng]), o ? [o] : []);
    if (path.length > 1) {
      L.polyline(path, { color: '#dc2626', weight: 3, dashArray: '6 6' }).addTo(map);
      path.forEach(p => all.push(p));
    }
    if (o) L.marker(o).addTo(map).bindPopup(__('Điểm xuất phát (Depot)'));
    stops.forEach(s => L.marker([s.lat, s.lng]).addTo(map).bindPopup(
      '#' + s.idx + ' ' + esc(s.customer || '') +
      (s.estimated_arrival ? '<br>ETA: ' + esc(String(s.estimated_arrival)) : '')));
    if (track.length > 1) {
      const pts = track.map(p => [p.latitude, p.longitude]);
      L.polyline(pts, { color: '#2563eb', weight: 4 }).addTo(map);
      pts.forEach(p => all.push(p));
    }
    if (veh && veh.custom_last_lat && veh.custom_last_lng) {
      const p = [veh.custom_last_lat, veh.custom_last_lng];
      L.circleMarker(p, { radius: 9, weight: 2, color: '#111', fillColor: '#16a34a', fillOpacity: 0.9 })
        .addTo(map).bindPopup(esc(frm.doc.vehicle) + '<br>' + esc(String(veh.custom_last_gps_time || '')));
      all.push(p);
    }
    map.invalidateSize();
    map.fitBounds(L.latLngBounds(all), { padding: [30, 30] });
  }, 300);
};

const DP_STATE = {
	"Picked Up": ["Đã lấy hàng", "#2563eb"],
	Assigned: ["Đã phân công", "#64748b"],
	"In Transit": ["Đang giao", "#2563eb"],
	Delivered: ["Đã giao đủ", "#15803d"],
	Partial: ["Giao một phần", "#d97706"],
	Returned: ["Đã hoàn/trả", "#7c3aed"],
	Exception: ["Có sự cố", "#dc2626"],
};

async function dp_stop_board(frm) {
	if (!frm.doc.name || frm.is_new()) return;
	try {
		const response = await frappe.call({ method: "dp_dispatch.completion.get_stop_board", args: { trip: frm.doc.name } });
		const stops = response.message || [];
		if (!stops.length) return;
		const cards = stops.map((stop, index) => {
			const [label, color] = DP_STATE[stop.status] || DP_STATE.Assigned;
			const order = stop.order ? `<a href="/app/delivery-order/${encodeURIComponent(stop.order)}">${frappe.utils.escape_html(stop.order)}</a>` : "Điểm theo Delivery Note";
			const q = stop.quantities || {};
			return `<div style="min-width:225px;max-width:290px;border:2px solid ${color};border-radius:12px;padding:12px;background:var(--card-bg)">
				<div style="font-size:12px;color:#64748b">ĐIỂM ${index + 1} · ${{Pickup:"Lấy hàng",Delivery:"Giao hàng",Return:"Trả người gửi"}[stop.operation] || "Giao hàng"}</div><strong>${frappe.utils.escape_html(stop.customer || "Điểm giao")}</strong>
				<div style="margin:6px 0;color:${color};font-weight:700">● ${label}</div><div>${order}</div>
				<div style="margin-top:6px">${frappe.utils.escape_html(stop.address || "")}</div>
				${stop.window_start ? `<div style="font-size:12px;margin-top:6px">Khung giờ: ${frappe.utils.escape_html(String(stop.window_start))} → ${frappe.utils.escape_html(String(stop.window_end))}<br>Đến dự kiến: ${frappe.utils.escape_html(String(stop.planned_arrival || ""))}<br>Tải dự kiến sau điểm: ${flt(stop.load_after_kg)} kg</div>` : ""}
				${stop.total ? `<div style="margin-top:8px"><b>Cần giao:</b> ${frappe.utils.escape_html(stop.total)}</div>` : ""}
				<div style="margin-top:6px;font-size:12px">Đã lấy: ${q.picked_up || 0} · Đã giao: ${q.delivered || 0} · Đã trả người gửi: ${q.returned_to_sender || 0}</div>
				<div style="font-size:12px">Hoàn/trả: ${q.returned || 0} · Còn chờ: ${q.pending || 0}</div>
			</div>`;
		}).join("");
		const total = frm.doc.custom_total_delivery_qty ? `<div style="font-weight:700;margin:4px 0 8px">Tổng hàng cả chuyến: ${frappe.utils.escape_html(frm.doc.custom_total_delivery_qty)}</div>` : "";
		const onboard = frm.doc.custom_transport_mode === "Pickup and Delivery" ? `<div>Hàng trên xe: ${frappe.utils.escape_html(frm.doc.custom_onboard_quantity || "0")} · ${flt(frm.doc.custom_onboard_weight_kg)} kg</div>` : "";
		frm.dashboard.set_headline(`${total}${onboard}<div style="display:flex;gap:10px;overflow-x:auto;padding:10px 2px">${cards}</div>`);
	} catch (e) {
		// The trip form itself remains usable if the summary endpoint is unavailable.
	}
}

async function dp_update_order_totals(frm) {
	if (frm.doc.custom_transport_mode === "Pickup and Delivery") return; // Server computes peak load by route sequence.
	if (frm.doc.docstatus !== 0) return;
	const stops = frm.doc.delivery_stops || [];
	const orders = [...new Set(stops.map(s => s.custom_delivery_order).filter(Boolean))];
	if (!orders.length) return;
	const records = await Promise.all(orders.map(name => frappe.db.get_value("Delivery Order", name, ["total_quantity_display", "total_weight_kg"])));
	const byUom = {};
	let weight = 0;
	for (const response of records) {
		const row = response.message || {};
		weight += flt(row.total_weight_kg);
		for (const part of (row.total_quantity_display || "").split(" + ")) {
			const match = part.match(/^([\d.]+)\s+(.+)$/);
			if (match) byUom[match[2]] = (byUom[match[2]] || 0) + flt(match[1]);
		}
	}
	await frm.set_value("custom_total_delivery_qty", Object.entries(byUom).map(([unit, qty]) => `${Number(qty.toFixed(3))} ${unit}`).join(" + "));
	await frm.set_value("custom_planned_load_kg", weight);
}

frappe.ui.form.on("Delivery Trip", {
	onload(frm) {
		if (frm.is_new()) frm.set_value("custom_transport_mode", "Pickup and Delivery");
	},
	setup(frm) {
		dp_configure_stop_grid(frm);
		frm.set_query("custom_delivery_order", "delivery_stops", () => ({
			filters: { docstatus: 1, delivery_status: "Pending Assignment" },
		}));
	},
	refresh(frm) {
		dp_configure_stop_grid(frm);
		dp_stop_board(frm);
		if (!frm.is_new()) {
			frm.add_custom_button(__("Xem bản đồ GPS"), () => dp_gps.show_trip_map(frm), __("GPS"));
			frm.add_custom_button(__("Fleet Map"), () => frappe.set_route("fleet-map"), __("GPS"));
		}
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Thêm đơn lấy–giao"), () => frappe.prompt([
				{fieldname:"order",label:__("Đơn vận chuyển"),fieldtype:"Link",options:"Delivery Order",reqd:1,
				 get_query: () => ({filters:{docstatus:1,delivery_status:"Pending Assignment"}})}
			], async values => {
				if ((frm.doc.delivery_stops || []).some(s => s.custom_delivery_order === values.order)) return frappe.msgprint(__("Đơn đã có trên chuyến."));
				const {message} = await frappe.call({method:"dp_dispatch.transport.order_stops",args:{order_name:values.order}});
				await frm.set_value("custom_transport_mode", "Pickup and Delivery");
				for (const row of message || []) frm.add_child("delivery_stops", row);
				frm.refresh_field("delivery_stops");
			}, __("Thêm điểm lấy và giao")));
		}
		if (frm.doc.docstatus !== 1) return;
		const roles = frappe.user_roles || [];
		const isDriver = roles.includes("DP Driver") && !roles.includes("System Manager");
		const isAdmin = roles.includes("System Manager") || frappe.session.user === "Administrator";
		const isFleetManager = roles.includes("Fleet Manager");
		const run = async (method, args = {}) => {
			await frappe.call({ method: `dp_dispatch.completion.${method}`, args: { trip: frm.doc.name, ...args }, freeze: true });
			await frm.reload_doc();
		};
		if ((isDriver || isAdmin || isFleetManager) && frm.doc.status === "Scheduled" && !frm.doc.custom_started_at) {
			frm.add_custom_button(__("Bắt đầu chuyến"), () => frappe.confirm(
				__("Xác nhận chuyến đã bắt đầu?"), () => run("start_trip")));
		}
		if ((isDriver || isAdmin || isFleetManager) && frm.doc.status === "In Transit" && !frm.doc.custom_completed_at) {
			frm.add_custom_button(__("Ghi nhận giao/hoàn hàng"), () => {
				const stops = (frm.doc.delivery_stops || []).filter(stop => !["Delivered", "Returned", "Picked Up", "Partial"].includes(stop.custom_delivery_state));
				if (!stops.length) return frappe.msgprint(__("Các điểm hiện đã có kết quả cuối."));
				frappe.prompt([{ fieldname: "stop", label: __("Điểm giao"), fieldtype: "Select", reqd: 1,
					options: stops.map(stop => ({ value: stop.name, label: dp_stop_label(stop) })) }],
					values => frappe.new_doc("Delivery Confirmation", { delivery_trip: frm.doc.name, delivery_stop: values.stop }),
					__("Chọn điểm giao"), __("Tiếp tục"));
			});
		}
		const completionState = frm.doc.custom_completion_status || "Open";
		if (isDriver && frm.doc.status === "In Transit" && frm.doc.custom_started_at && !["Approved", "Requested", "Exception Requested", "Exception Closed"].includes(completionState)) {
			frm.add_custom_button(__("Gửi yêu cầu kết thúc chuyến"), () => frappe.confirm(
				__("Gửi cho Admin duyệt? Mỗi điểm phải có xác nhận giao nhận, không còn hàng chờ và đã thu đủ phí."),
				() => run("request_completion")));
			frm.add_custom_button(__("Báo sự cố / nhờ Admin kết thúc"), () => frappe.prompt(
				[{ fieldname: "note", label: __("Mô tả sự cố và điểm chưa thể giao"), fieldtype: "Small Text", reqd: 1 }],
				values => run("request_incident_closure", values), __("Báo sự cố chuyến"), __("Gửi Admin")));
		}
		if (isAdmin && frm.doc.custom_completion_status === "Requested") {
			frm.add_custom_button(__("Từ chối yêu cầu"), () => frappe.prompt(
				[{ fieldname: "note", label: __("Lý do"), fieldtype: "Small Text", reqd: 1 }],
				values => run("reject_completion", values), __("Từ chối hoàn tất"), __("Gửi")));
			frm.add_custom_button(__("Duyệt hoàn tất chuyến"), () => frappe.prompt(
				[{ fieldname: "note", label: __("Ghi chú duyệt"), fieldtype: "Small Text" }],
				values => run("approve_completion", values), __("Duyệt hoàn tất"), __("Xác nhận")));
		}
		if (isAdmin && frm.doc.custom_completion_status === "Exception Requested") {
			frm.add_custom_button(__("Kết thúc chuyến do sự cố"), () => frappe.prompt(
				[{ fieldname: "note", label: __("Ghi chú xử lý của Admin"), fieldtype: "Small Text" }],
				values => run("close_trip_for_incident", values), __("Đóng chuyến do sự cố"), __("Xác nhận đóng")));
		}
	},
	vehicle(frm) {
		if (!frm.doc.vehicle) return frm.set_value("custom_vehicle_capacity_kg", 0);
		frappe.db.get_value("Vehicle", frm.doc.vehicle, "custom_payload_capacity_kg").then(({ message }) => {
			frm.set_value("custom_vehicle_capacity_kg", message?.custom_payload_capacity_kg || 0);
		});
	},
});

function dp_stop_label(stop) {
	const customer = stop.customer || "Khách chưa xác định";
	const destination = stop.customer_address || stop.address || "Chưa có địa chỉ";
	const source = stop.custom_delivery_order || stop.delivery_note || "Chưa gắn đơn";
	const kind = {Pickup:"Lấy hàng",Delivery:"Giao hàng",Return:"Trả người gửi"}[stop.custom_stop_type] || "Giao hàng";
	return `${stop.idx}. ${kind}: ${customer} — ${destination} (${source})`;
}

function dp_configure_stop_grid(frm) {
	const grid = frm.fields_dict.delivery_stops?.grid;
	if (!grid) return;
	// Delivery Order is the active stock-free workflow. Keep the legacy
	// Delivery Note field in the schema for older trips, but remove it from
	// the dispatcher-facing grid to prevent choosing the warehouse flow by mistake.
	grid.update_docfield_property("delivery_note", "hidden", 1);
	grid.update_docfield_property("custom_delivery_order", "hidden", 0);
	grid.update_docfield_property("custom_delivery_order", "in_list_view", 1);
}

frappe.ui.form.on("Delivery Stop", {
	async custom_delivery_order(frm, cdt, cdn) {
		const stop = locals[cdt][cdn];
		const orderName = stop.custom_delivery_order;
		if (!orderName) {
			await frappe.model.set_value(cdt, cdn, "customer", "");
			await frappe.model.set_value(cdt, cdn, "address", "");
			await frappe.model.set_value(cdt, cdn, "customer_address", "");
			frm.refresh_field("delivery_stops");
			return dp_update_order_totals(frm);
		}
		const { message } = await frappe.db.get_value("Delivery Order", orderName,
			["customer", "shipping_address", "delivery_address", "pickup_address_link", "pickup_address"]);
		// Ignore a late response if the user selected a different order meanwhile.
		if (!message || locals[cdt][cdn].custom_delivery_order !== orderName) return;
		await frappe.model.set_value(cdt, cdn, "customer", message.customer || "");
		const pickup = ["Pickup", "Return"].includes(stop.custom_stop_type);
		await frappe.model.set_value(cdt, cdn, "address", (pickup ? message.pickup_address_link : message.shipping_address) || "");
		await frappe.model.set_value(cdt, cdn, "customer_address", (pickup ? message.pickup_address : message.delivery_address) || "");
		frm.refresh_field("delivery_stops");
		return dp_update_order_totals(frm);
	},
	custom_delivery_state(frm) { dp_stop_board(frm); },
	visited(frm) { dp_stop_board(frm); },
	form_render(frm) { dp_stop_board(frm); },
});

frappe.listview_settings['Delivery Trip'] = frappe.listview_settings['Delivery Trip'] || {};
(function () {
  const settings = frappe.listview_settings['Delivery Trip'];
  const previous = settings.onload;
  settings.onload = function (listview) {
    if (previous) previous(listview);
    listview.page.add_inner_button(__('Fleet Map'), () => frappe.set_route('fleet-map'));
  };
})();

