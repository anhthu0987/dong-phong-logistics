function dp_vehicle_log_is_driver() {
	const roles = frappe.user_roles || [];
	return roles.includes("DP Driver") && !roles.includes("System Manager");
}

function dp_vehicle_log_is_reviewer() {
	const roles = frappe.user_roles || [];
	return frappe.session.user === "Administrator" || roles.includes("System Manager") || roles.includes("Fleet Manager");
}

frappe.ui.form.on("Vehicle Log", {
	setup(frm) {
		frm.set_query("custom_delivery_trip", () => ({ filters: { docstatus: 1, status: "In Transit" } }));
	},
	refresh(frm) {
		const driver = dp_vehicle_log_is_driver();
		const reviewer = dp_vehicle_log_is_reviewer();
		const state = frm.doc.custom_approval_status || "Draft";
		const locked = driver && !["Draft", "Needs Correction"].includes(state);

		if (driver) {
			frm.set_df_property("employee", "read_only", 1);
			frm.set_df_property("license_plate", "read_only", 1);
			["employee", "license_plate", "custom_delivery_trip", "custom_expense_type", "custom_expense_amount",
				"custom_expense_note", "custom_receipt", "fuel_qty", "price", "last_odometer", "odometer"].forEach(field => {
				frm.set_df_property(field, "read_only", locked ? 1 : 0);
			});
		}

		const isFuel = frm.doc.custom_expense_type === "Fuel";
		frm.set_df_property("fuel_qty", "hidden", driver && !isFuel ? 1 : 0);
		frm.set_df_property("price", "hidden", driver && !isFuel ? 1 : 0);
		frm.set_df_property("service_detail", "hidden", driver ? 1 : 0);

		if (frm.doc.docstatus === 0 && frm.doc.name && driver && ["Draft", "Needs Correction"].includes(state)) {
			frm.add_custom_button(__("Gửi Admin duyệt"), async () => {
				await frm.save();
				await frappe.call({
					method: "dp_dispatch.maintenance.send_vehicle_log_for_review",
					args: { name: frm.doc.name }, freeze: true,
				});
				await frm.reload_doc();
			});
		}

		if (frm.doc.docstatus === 0 && state === "Pending Review" && reviewer) {
			frm.add_custom_button(__("Duyệt chi phí"), async () => {
				await frappe.confirm(__("Xác nhận chi phí và Submit Vehicle Log này?"), async () => {
					await frappe.call({
						method: "dp_dispatch.maintenance.review_vehicle_log",
						args: { name: frm.doc.name, action: "Approve" }, freeze: true,
					});
					await frm.reload_doc();
				});
			}, __("Duyệt"));

			frm.add_custom_button(__("Trả lại bổ sung"), () => dp_vehicle_log_review_prompt(frm, "Return"), __("Duyệt"));
			frm.add_custom_button(__("Từ chối"), () => dp_vehicle_log_review_prompt(frm, "Reject"), __("Duyệt"));
		}

		if (state === "Pending Review") {
			frm.set_intro(__("Vehicle Log đang chờ Admin/Fleet Manager kiểm tra."), "blue");
		} else if (state === "Needs Correction") {
			frm.set_intro(__("Admin yêu cầu bổ sung. Xem Ý kiến Admin, cập nhật rồi gửi duyệt lại."), "orange");
		} else if (state === "Rejected") {
			frm.set_intro(__("Vehicle Log đã bị từ chối. Xem Ý kiến Admin để biết lý do."), "red");
		} else if (state === "Approved") {
			frm.set_intro(__("Chi phí đã được duyệt."), "green");
		}
	},
	custom_delivery_trip(frm) {
		if (!frm.doc.custom_delivery_trip) return;
		frappe.call({
			method: "dp_dispatch.maintenance.get_vehicle_log_defaults",
			args: { delivery_trip: frm.doc.custom_delivery_trip },
		}).then(({ message }) => {
			if (!message || frm.doc.custom_delivery_trip !== message.delivery_trip) return;
			frm.set_value("license_plate", message.license_plate);
			frm.set_value("employee", message.employee);
			frm.set_value("last_odometer", message.last_odometer);
		});
	},
	custom_expense_type(frm) {
		if (frm.doc.custom_expense_type === "Fuel") {
			frm.set_value("custom_expense_amount", flt(frm.doc.fuel_qty) * flt(frm.doc.price));
		}
	},
	fuel_qty(frm) { dp_vehicle_log_update_fuel_total(frm); },
	price(frm) { dp_vehicle_log_update_fuel_total(frm); },
});

function dp_vehicle_log_update_fuel_total(frm) {
	if (frm.doc.custom_expense_type === "Fuel") {
		frm.set_value("custom_expense_amount", flt(frm.doc.fuel_qty) * flt(frm.doc.price));
	}
}

function dp_vehicle_log_review_prompt(frm, action) {
	frappe.prompt([
		{ fieldname: "note", label: __("Ý kiến cho tài xế"), fieldtype: "Small Text", reqd: 1 },
	], async ({ note }) => {
		await frappe.call({
			method: "dp_dispatch.maintenance.review_vehicle_log",
			args: { name: frm.doc.name, action, note }, freeze: true,
		});
		await frm.reload_doc();
	}, action === "Return" ? __("Trả lại để bổ sung") : __("Từ chối Vehicle Log"), action === "Return" ? __("Gửi yêu cầu bổ sung") : __("Xác nhận từ chối"));
}
