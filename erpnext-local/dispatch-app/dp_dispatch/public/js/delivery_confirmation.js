function dp_load_confirmation_stops(frm) {
	if (!frm.is_new() || !frm.doc.delivery_trip || frm.doc.delivery_stop || frm.__dp_loading_stops) return;
	frm.__dp_loading_stops = true;
	const trip = frm.doc.delivery_trip;
	Promise.resolve(frappe.call({
		method: "dp_dispatch.delivery_confirmation.get_trip_stops",
		args: { delivery_trip: trip },
	})).then(({ message }) => {
		if (frm.doc.delivery_trip !== trip || frm.doc.delivery_stop) return;
		const stops = message || [];
		if (stops.length === 1) {
			frm.set_value("delivery_stop", stops[0].value);
		} else if (stops.length > 1) {
			frappe.prompt([{ fieldname: "stop", label: __("Điểm giao"), fieldtype: "Select", options: stops, reqd: 1 }],
				values => frm.set_value("delivery_stop", values.stop), __("Chọn điểm giao"), __("Tiếp tục"));
		} else if (!stops.length) {
			frappe.msgprint(__("Không tìm thấy điểm giao trên chuyến này. Hãy kiểm tra Delivery Stops của chuyến hoặc liên hệ điều phối viên."));
		}
	}).catch((error) => {
		console.error("Could not load Delivery Trip stops", error);
		frappe.msgprint(__("Không tải được danh sách điểm giao. Nếu chuyến chỉ có một điểm giao, bạn vẫn có thể lưu phiếu; hệ thống sẽ tự xác định điểm đó. Nếu có nhiều điểm, hãy nhờ điều phối viên kiểm tra quyền truy cập."));
	}).finally(() => { frm.__dp_loading_stops = false; });
}

frappe.ui.form.on("Delivery Confirmation", {
	onload(frm) {
		frm.__dp_last_trip = frm.doc.delivery_trip || "";
	},
	refresh(frm) {
		dp_load_confirmation_stops(frm);
		// Read-only route defaults do not always emit field events in Frappe.
		if (frm.is_new() && frm.doc.delivery_stop && frm.__dp_loaded_stop !== frm.doc.delivery_stop) {
			frm.trigger("delivery_stop");
		}
		dp_confirmation_operation(frm);
	},
	setup(frm) {
	},
	delivery_trip(frm) {
		const previousTrip = frm.__dp_last_trip || "";
		if (previousTrip === (frm.doc.delivery_trip || "")) return;
		frm.__dp_last_trip = frm.doc.delivery_trip || "";
		// Frappe may apply route_options after onload. The first trip value is
		// initialization; do not clear a stop passed by the Delivery Trip action.
		if (!previousTrip) {
			dp_load_confirmation_stops(frm);
			return;
		}
		frm.set_value("delivery_stop", "");
		frm.set_value("delivery_order", "");
		frm.set_value("delivery_note", "");
		dp_load_confirmation_stops(frm);
	},
	delivery_stop(frm) {
		if (!frm.doc.delivery_stop) return;
		const stop = frm.doc.delivery_stop;
		if (frm.__dp_loading_details === stop) return;
		frm.__dp_loading_details = stop;
		frm.set_value("delivery_order", "");
		frm.set_value("delivery_note", "");
		return Promise.resolve(frappe.call({
			method: "dp_dispatch.delivery_confirmation.get_stop_details",
			args: { delivery_trip: frm.doc.delivery_trip, delivery_stop: frm.doc.delivery_stop },
		})).then(({ message }) => {
			if (!message || frm.doc.delivery_stop !== stop) return;
			frm.__dp_loaded_stop = stop;
			frm.set_value("delivery_order", message.delivery_order || "");
			frm.set_value("operation", message.operation || "Delivery");
			dp_confirmation_operation(frm);
			frm.set_value("delivery_note", message.delivery_note || "");
			frm.set_value("shipping_fee_due", message.shipping_fee || 0);
			frm.clear_table("items");
			for (const item of (message.items || [])) {
				frm.add_child("items", {
					...item,
					delivered_qty: 0,
					returned_qty: 0,
					pending_qty: item.allocated_qty || 0,
				});
			}
			frm.refresh_field("items");
		}).finally(() => {
			if (frm.__dp_loading_details === stop) frm.__dp_loading_details = null;
		});
	},
});

function dp_confirmation_operation(frm) {
	const kind = frm.doc.operation || "Delivery";
	const grid = frm.fields_dict.items?.grid;
	if (!grid) return;
	grid.update_docfield_property("picked_up_qty", "hidden", kind !== "Pickup");
	grid.update_docfield_property("delivered_qty", "hidden", kind !== "Delivery");
	grid.update_docfield_property("returned_qty", "hidden", kind !== "Delivery");
	grid.update_docfield_property("returned_qty", "label", "Cần trả người gửi (còn trên xe)");
	grid.update_docfield_property("returned_to_sender_qty", "hidden", kind !== "Return");
	frm.toggle_display(["shipping_fee_due", "shipping_fee_collected", "fee_collection_method"], kind === "Delivery");
}
