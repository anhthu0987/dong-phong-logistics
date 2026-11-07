const DP_STATE = {
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
				<div style="font-size:12px;color:#64748b">ĐIỂM ${index + 1}</div><strong>${frappe.utils.escape_html(stop.customer || "Điểm giao")}</strong>
				<div style="margin:6px 0;color:${color};font-weight:700">● ${label}</div><div>${order}</div>
				<div style="margin-top:6px">${frappe.utils.escape_html(stop.address || "")}</div>
				${stop.total ? `<div style="margin-top:8px"><b>Cần giao:</b> ${frappe.utils.escape_html(stop.total)}</div>` : ""}
				<div style="margin-top:6px;font-size:12px">Đã phân: ${q.allocated || 0} · Đã nhận: ${q.delivered || 0}</div>
				<div style="font-size:12px">Hoàn/trả: ${q.returned || 0} · Còn chờ: ${q.pending || 0}</div>
			</div>`;
		}).join("");
		const total = frm.doc.custom_total_delivery_qty ? `<div style="font-weight:700;margin:4px 0 8px">Tổng hàng cả chuyến: ${frappe.utils.escape_html(frm.doc.custom_total_delivery_qty)}</div>` : "";
		frm.dashboard.set_headline(`${total}<div style="display:flex;gap:10px;overflow-x:auto;padding:10px 2px">${cards}</div>`);
	} catch (e) {
		// The trip form itself remains usable if the summary endpoint is unavailable.
	}
}

async function dp_update_order_totals(frm) {
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
	setup(frm) {
		dp_configure_stop_grid(frm);
		frm.set_query("custom_delivery_order", "delivery_stops", () => ({
			filters: { docstatus: 1, delivery_status: "Pending Assignment" },
		}));
	},
	refresh(frm) {
		dp_configure_stop_grid(frm);
		dp_stop_board(frm);
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
		if (isDriver && frm.doc.status === "In Transit" && !frm.doc.custom_completed_at) {
			frm.add_custom_button(__("Ghi nhận giao/hoàn hàng"), () => {
				const stops = (frm.doc.delivery_stops || []).filter(stop => !["Delivered", "Returned"].includes(stop.custom_delivery_state));
				if (!stops.length) return frappe.msgprint(__("Các điểm hiện đã có kết quả cuối."));
				frappe.prompt([{ fieldname: "stop", label: __("Điểm giao"), fieldtype: "Select", reqd: 1,
					options: stops.map(stop => ({ value: stop.name, label: dp_stop_label(stop) })) }],
					values => frappe.new_doc("Delivery Confirmation", { delivery_trip: frm.doc.name, delivery_stop: values.stop }),
					__("Chọn điểm giao"), __("Tiếp tục"));
			});
		}
		if (isDriver && frm.doc.custom_started_at && !["Approved", "Requested"].includes(frm.doc.custom_completion_status)) {
			frm.add_custom_button(__("Gửi yêu cầu kết thúc chuyến"), () => frappe.confirm(
				__("Gửi cho Admin duyệt? Mỗi điểm phải có xác nhận giao nhận, không còn hàng chờ và đã thu đủ phí."),
				() => run("request_completion")));
		}
		if (isAdmin && frm.doc.custom_completion_status === "Requested") {
			frm.add_custom_button(__("Từ chối yêu cầu"), () => frappe.prompt(
				[{ fieldname: "note", label: __("Lý do"), fieldtype: "Small Text", reqd: 1 }],
				values => run("reject_completion", values), __("Từ chối hoàn tất"), __("Gửi")));
			frm.add_custom_button(__("Duyệt hoàn tất chuyến"), () => frappe.prompt(
				[{ fieldname: "note", label: __("Ghi chú duyệt"), fieldtype: "Small Text" }],
				values => run("approve_completion", values), __("Duyệt hoàn tất"), __("Xác nhận")));
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
	return `${stop.idx}. ${customer} — ${destination} (${source})`;
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
			["customer", "shipping_address", "delivery_address"]);
		// Ignore a late response if the user selected a different order meanwhile.
		if (!message || locals[cdt][cdn].custom_delivery_order !== orderName) return;
		await frappe.model.set_value(cdt, cdn, "customer", message.customer || "");
		await frappe.model.set_value(cdt, cdn, "address", message.shipping_address || "");
		await frappe.model.set_value(cdt, cdn, "customer_address", message.delivery_address || "");
		frm.refresh_field("delivery_stops");
		return dp_update_order_totals(frm);
	},
	custom_delivery_state(frm) { dp_stop_board(frm); },
	visited(frm) { dp_stop_board(frm); },
	form_render(frm) { dp_stop_board(frm); },
});
