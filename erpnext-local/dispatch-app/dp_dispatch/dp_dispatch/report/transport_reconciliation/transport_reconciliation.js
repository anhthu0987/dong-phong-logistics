frappe.query_reports['Transport Reconciliation'] = {
    filters: [
        {fieldname: 'company', label: __('Công ty'), fieldtype: 'Link', options: 'Company', reqd: 1,
         default: frappe.defaults.get_user_default('Company')},
        {fieldname: 'delivery_trip', label: __('Chuyến'), fieldtype: 'Link', options: 'Delivery Trip'},
        {fieldname: 'from_date', label: __('Khởi hành từ ngày'), fieldtype: 'Date'},
        {fieldname: 'to_date', label: __('Đến ngày'), fieldtype: 'Date'},
    ],
};
