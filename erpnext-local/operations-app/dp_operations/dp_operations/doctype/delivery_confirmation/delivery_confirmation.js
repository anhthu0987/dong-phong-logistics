frappe.ui.form.on('Delivery Confirmation', {
    refresh: function(frm) {
        render_delivery_summary(frm);
    },
    validate: function(frm) {
        render_delivery_summary(frm);
    }
});

frappe.ui.form.on('Delivery Confirmation Item', {
    received_qty: function(frm) { render_delivery_summary(frm); },
    returned_qty: function(frm) { render_delivery_summary(frm); },
    pending_qty: function(frm) { render_delivery_summary(frm); },
    items_remove: function(frm) { render_delivery_summary(frm); }
});

function render_delivery_summary(frm) {
    if (!frm.doc.items || frm.doc.items.length === 0) return;

    let total_allocated = 0;
    let total_received = 0;
    let total_returned = 0;
    let total_pending = 0;

    frm.doc.items.forEach(row => {
        total_allocated += flt(row.allocated_qty);
        total_received += flt(row.received_qty);
        total_returned += flt(row.returned_qty);
        total_pending += flt(row.pending_qty);
    });

    if (total_allocated === 0) return;

    let success_rate = Math.round((total_received / total_allocated) * 100);
    let return_rate = Math.round((total_returned / total_allocated) * 100);

    let bar_color = "bg-success";
    let indicator_color = "green";
    let status_text = "Giao hàng xuất sắc (100%)";

    if (total_returned > 0) {
        bar_color = "bg-warning";
        indicator_color = "orange";
        status_text = `Phát sinh trả hàng (${total_returned} món)`;
    } else if (success_rate < 100) {
        bar_color = "bg-info";
        indicator_color = "blue";
        status_text = `Đang giao dở dang (${success_rate}%)`;
    }

    let html = `
        <div style="padding: 12px; background: #f8f9fa; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: 600; font-size: 13px;">
                    <span class="indicator-pill ${indicator_color}"></span> Tiến độ giao hàng: ${success_rate}%
                </span>
                <span style="font-size: 12px; color: #6c757d; font-weight: 500;">
                    ${status_text}
                </span>
            </div>
            <div class="progress" style="height: 10px; border-radius: 5px; background-color: #e9ecef; overflow: hidden; display: flex;">
                <div class="progress-bar ${bar_color}" role="progressbar" style="width: ${success_rate}%;"></div>
                <div class="progress-bar bg-danger" role="progressbar" style="width: ${return_rate}%;"></div>
            </div>
            <div style="display: flex; gap: 20px; margin-top: 10px; font-size: 12px;">
                <div>📦 <b>Phân giao:</b> ${total_allocated}</div>
                <div>✅ <b>Khách nhận:</b> <span style="color: #28a745; font-weight: bold;">${total_received}</span></div>
                <div>↩️ <b>Trả về:</b> <span style="color: #dc3545; font-weight: bold;">${total_returned}</span></div>
                <div>⏳ <b>Chờ xử lý:</b> <span style="color: #fd7e14; font-weight: bold;">${total_pending}</span></div>
            </div>
        </div>
    `;

    frm.dashboard.clear_headline();
    frm.dashboard.set_headline(html);
}