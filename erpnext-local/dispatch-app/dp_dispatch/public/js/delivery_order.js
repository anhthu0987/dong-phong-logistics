function dp_order_totals(frm) {
	const byUom = {};
	let weight = 0;
	for (const row of (frm.doc.items || [])) {
		const unit = row.uom || "kiện";
	byUom[unit] = (byUom[unit] || 0) + flt(row.qty);
	weight += flt(row.qty) * flt(row.weight_kg);
	}
	frm.set_value("total_quantity_display", Object.entries(byUom).map(([unit, qty]) => `${Number(qty.toFixed(3))} ${unit}`).join(" + "));
	frm.set_value("total_weight_kg", Number(weight.toFixed(3)));
}

frappe.ui.form.on("Delivery Order", {
	refresh(frm) {
		dp_order_totals(frm);
		frm.dashboard.clear_headline();
		if (frm.doc.total_quantity_display) {
			frm.dashboard.set_headline(`<b>Tổng hàng:</b> ${frappe.utils.escape_html(frm.doc.total_quantity_display)} · <b>Khối lượng:</b> ${frappe.utils.escape_html(String(frm.doc.total_weight_kg || 0))} kg`);
		}
	},
	items_add(frm) { dp_order_totals(frm); },
	items_remove(frm) { dp_order_totals(frm); },
});

frappe.ui.form.on("Delivery Order Item", {
	qty(frm) { dp_order_totals(frm); },
	uom(frm) { dp_order_totals(frm); },
	weight_kg(frm) { dp_order_totals(frm); },
	item_code(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.item_code || row.description) return;
		frappe.db.get_value("Item", row.item_code, ["item_name", "stock_uom"]).then(({ message }) => {
			if (!message) return;
			frappe.model.set_value(cdt, cdn, "description", message.item_name || row.item_code);
			if (!row.uom) frappe.model.set_value(cdt, cdn, "uom", message.stock_uom || "kiện");
		});
	},
});
