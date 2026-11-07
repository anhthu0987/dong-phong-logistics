async function set_record_from_plan(frm, plan_name) {
	if (!plan_name) {
		await frm.set_value("service_item", "");
		return;
	}

	const { message } = await frappe.db.get_value(
		"Fleet Maintenance Plan",
		plan_name,
		["vehicle", "service_item"]
	);
	if (frm.doc.maintenance_plan !== plan_name) return;
	if (!message) {
		frappe.msgprint(__("Không tìm thấy kế hoạch bảo dưỡng đã chọn."));
		return;
	}

	await frm.set_value("vehicle", message.vehicle || "");
	await frm.set_value("service_item", message.service_item || "");
}

frappe.ui.form.on("Fleet Maintenance Record", {
	maintenance_plan(frm) {
		set_record_from_plan(frm, frm.doc.maintenance_plan);
	},

	async vehicle(frm) {
		const selectedVehicle = frm.doc.vehicle;
		if (!selectedVehicle) {
			await frm.set_value("maintenance_plan", "");
			await frm.set_value("service_item", "");
			return;
		}

		// Keep the selected service item when its selected plan belongs to this vehicle.
		if (frm.doc.maintenance_plan) {
			const currentPlan = frm.doc.maintenance_plan;
			const { message } = await frappe.db.get_value(
				"Fleet Maintenance Plan",
				currentPlan,
				["vehicle", "service_item"]
			);
			if (frm.doc.vehicle !== selectedVehicle) return;
			if (frm.doc.maintenance_plan !== currentPlan) return;
			if (message && message.vehicle === selectedVehicle) {
				await frm.set_value("service_item", message.service_item || "");
				return;
			}
			await frm.set_value("maintenance_plan", "");
		}

		const plans = await frappe.db.get_list("Fleet Maintenance Plan", {
			filters: {
				vehicle: selectedVehicle,
				status: ["in", ["Planned", "In Progress", "Out of Service"]],
			},
			fields: ["name", "service_item"],
			order_by: "modified desc",
			limit: 100,
		});
		if (frm.doc.vehicle !== selectedVehicle) return;

		if (!plans.length) {
			await frm.set_value("maintenance_plan", "");
			await frm.set_value("service_item", "");
			frappe.msgprint(__("Xe này chưa có kế hoạch bảo dưỡng đang hoạt động. Hãy tạo/chọn kế hoạch trước."));
			return;
		}

		if (plans.length === 1) {
			await frm.set_value("maintenance_plan", plans[0].name);
			await frm.set_value("service_item", plans[0].service_item || "");
			return;
		}

		const options = plans.map((plan) =>
			`${plan.name} — ${plan.service_item || "Chưa chọn hạng mục"}`
		);
		const dialog = new frappe.ui.Dialog({
			title: __("Chọn kế hoạch bảo dưỡng"),
			fields: [{
				fieldname: "maintenance_plan",
				label: __("Kế hoạch"),
				fieldtype: "Select",
				options,
				reqd: 1,
			}],
			primary_action_label: __("Chọn"),
			primary_action: async (values) => {
				dialog.hide();
				if (frm.doc.vehicle !== selectedVehicle) return;
				const plan = plans.find((row) =>
					`${row.name} — ${row.service_item || "Chưa chọn hạng mục"}` === values.maintenance_plan
				);
				if (!plan) return;
				await frm.set_value("maintenance_plan", plan.name);
				await frm.set_value("service_item", plan.service_item || "");
			},
		});
		dialog.show();
	},
});
