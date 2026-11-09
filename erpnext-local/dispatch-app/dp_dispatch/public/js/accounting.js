/* All accounting buttons use server permissions; standard forms review/submit. */
(() => {
    const accountant = () => frappe.session.user === 'Administrator' ||
        ['Accounts User', 'Accounts Manager', 'System Manager'].some(r => (frappe.user_roles || []).includes(r));
    const create = async (method, args, doctype) => {
        const {message} = await frappe.call({method: `dp_dispatch.accounting.${method}`, args, freeze: true});
        if (message) frappe.set_route('Form', doctype, message);
    };
    frappe.ui.form.on('Delivery Order', {
        refresh(frm) {
            if (!accountant() || frm.doc.docstatus !== 1) return;
            frm.add_custom_button(__('Lập / mở hóa đơn cước'), () => frappe.prompt([
                {fieldname: 'trip_name', label: __('Chuyến đã hoàn tất'), fieldtype: 'Link', options: 'Delivery Trip', reqd: 1,
                 get_query: () => ({filters: {docstatus: 1, custom_completion_status: 'Approved'}})},
            ], values => create('make_invoice', {order_name: frm.doc.name, ...values}, 'Sales Invoice'), __('Lập hóa đơn cước')), __('Kế toán'));
            frm.add_custom_button(__('Xem hóa đơn cước'), () => frappe.set_route('List', 'Sales Invoice', {custom_delivery_order: frm.doc.name}), __('Kế toán'));
        },
    });
    frappe.ui.form.on('Delivery Confirmation', {
        refresh(frm) {
            if (!accountant() || frm.doc.docstatus !== 1 || !frm.doc.shipping_fee_collected) return;
            frm.add_custom_button(__('Hạch toán tiền thực thu'), () => frappe.prompt([
                {fieldname: 'paid_to', label: __('Tài khoản đang giữ tiền (quỹ tài xế / ngân hàng)'), fieldtype: 'Link', options: 'Account', reqd: 1,
                 get_query: () => ({filters: {is_group: 0, disabled: 0, account_type: ['in', ['Cash', 'Bank']]}})},
                {fieldname: 'reference_no', label: __('Mã giao dịch (bắt buộc khi vào ngân hàng)'), fieldtype: 'Data'},
            ], values => create('make_collection_payment', {confirmation_name: frm.doc.name, ...values}, 'Payment Entry'), __('Đối chiếu số tiền thực nhận')), __('Kế toán'));
        },
    });
    frappe.ui.form.on('Vehicle Log', {
        refresh(frm) {
            if (!accountant() || frm.doc.docstatus !== 1 || !frm.doc.custom_delivery_trip) return;
            frm.add_custom_button(__('Lập / mở bút toán chi phí'), () => frappe.prompt([
                {fieldname: 'expense_account', label: __('Tài khoản chi phí'), fieldtype: 'Link', options: 'Account', reqd: 1,
                 get_query: () => ({filters: {is_group: 0, disabled: 0, root_type: 'Expense'}})},
                {fieldname: 'offset_account', label: __('Tiền đã chi / khoản phải hoàn ứng'), fieldtype: 'Link', options: 'Account', reqd: 1,
                 get_query: () => ({filters: {is_group: 0, disabled: 0}})},
                {fieldname: 'cost_center', label: __('Trung tâm chi phí'), fieldtype: 'Link', options: 'Cost Center', reqd: 1,
                 get_query: () => ({filters: {is_group: 0}})},
            ], values => create('make_expense_entry', {vehicle_log: frm.doc.name, ...values}, 'Journal Entry'), __('Hạch toán chi phí đã duyệt')), __('Kế toán'));
        },
    });
    frappe.ui.form.on('Delivery Trip', {
        refresh(frm) {
            if (!accountant() || frm.is_new()) return;
            frm.add_custom_button(__('Đối soát doanh thu và chi phí'), () => {
                frappe.route_options = {company: frm.doc.company, delivery_trip: frm.doc.name};
                frappe.set_route('query-report', 'Transport Reconciliation');
            }, __('Kế toán'));
        },
    });
})();
