frappe.ui.form.on("Quotation", {
	refresh(frm) {
		if (frm.doc.docstatus !== 1 || frm.doc.quotation_to !== "Customer" || !frm.doc.party_name) return;
		if (!frm.doc.custom_customer_accepted) {
			frm.set_intro(__("Báo giá đang ở trạng thái Open chưa có nghĩa khách đã đồng ý. Hãy xác nhận với khách, đánh dấu ô ‘Khách hàng đã đồng ý báo giá’ và lưu trước khi tạo đơn vận chuyển."), "orange");
			return;
		}
		if (frm.doc.delivery_order) {
			frm.set_intro(__("Đơn vận chuyển {0} đã được tạo từ báo giá này.", [frm.doc.delivery_order]), "green");
			return;
		}
		frm.set_intro(__("Khách đã xác nhận đồng ý báo giá. Có thể tạo đơn vận chuyển từ báo giá này."), "green");

		frm.add_custom_button(__("Tạo đơn vận chuyển"), () => {
			frappe.confirm(__("Bạn xác nhận khách hàng đã đồng ý báo giá này và các điều khoản vận chuyển?"), () => {
				frappe.model.open_mapped_doc({
					method: "dp_dispatch.api.make_delivery_order_from_quotation",
					frm,
				});
			});
		}, __("Tác vụ"));
	},
});
