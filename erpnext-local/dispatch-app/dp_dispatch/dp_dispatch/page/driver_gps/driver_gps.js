frappe.pages['driver-gps'].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __('Lịch trình Tài xế'),
    single_column: true
  });

  $(wrapper).find('.page-content').css({ 'padding': '12px', 'margin': '0' });

  $(page.main).html(`
    <style>
      .dp-driver-container {
        font-family: var(--font-stack, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
        max-width: 600px;
        margin: 0 auto;
      }
      .dp-trip-card {
        background: #000000;
        color: #ffffff;
        padding: 16px;
        border-radius: 10px;
        margin-bottom: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
      }
      .dp-stop-card {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      }
      .dp-badge-status {
        display: inline-block;
        font-size: 11px;
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 700;
      }
      .dp-btn-map {
        background: #000000;
        color: #ffffff !important;
        border: 1px solid #000000;
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        text-decoration: none !important;
      }
      .dp-btn-complete {
        background: #16a34a;
        color: #ffffff !important;
        border: none;
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
        cursor: pointer;
      }
      .dp-btn-complete:hover {
        background: #15803d;
      }
    </style>

    <div class="dp-driver-container">
      <div class="dp-trip-card">
        <div style="font-size: 12px; color: #a1a1aa; text-transform: uppercase; letter-spacing: 0.5px;">Chuyến hàng đang thực hiện</div>
        <div id="driver-trip-title" style="font-size: 18px; font-weight: 700; margin-top: 4px;">Đang tải...</div>
        <div id="driver-vehicle-info" style="font-size: 13px; color: #e4e4e7; margin-top: 2px;"></div>
      </div>

      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <h4 style="margin: 0; font-size: 15px; font-weight: 700; color: #111827;">📍 Danh sách điểm hẹn</h4>
        <button id="btn-refresh-driver" class="btn btn-default btn-xs"><i class="fa fa-refresh"></i> Cập nhật</button>
      </div>

      <div id="driver-stops-list">
        <div style="text-align: center; color: #9ca3af; padding: 20px;">Đang tải điểm hẹn...</div>
      </div>
    </div>
  `);

  const esc = frappe.utils.escape_html;

  function loadDriverSchedule() {
    frappe.call({
      method: 'dp_dispatch.dp_dispatch.api.gps.get_driver_schedule',
      callback: function (r) {
        if (!r.message || !r.message.trip) {
          $('#driver-trip-title').text('Chưa có chuyến hàng');
          $('#driver-vehicle-info').text('Hiện tại chưa có chuyến xe active được phân công.');
          $('#driver-stops-list').html('<div style="text-align: center; color: #9ca3af; padding: 30px;">Không có điểm hẹn giao hàng nào.</div>');
          return;
        }

        const trip = r.message.trip;
        const stops = r.message.stops || [];

        $('#driver-trip-title').text(trip.name);
        $('#driver-vehicle-info').html('<i class="fa fa-truck" style="color:#ffffff; margin-right:4px;"></i> Xe: <b>' + esc(trip.vehicle || 'N/A') + '</b> | Tài xế: ' + esc(trip.driver_name || 'N/A'));

        const container = $('#driver-stops-list').empty();

        if (!stops.length) {
          container.html('<div style="text-align: center; color: #9ca3af; padding: 20px;">Chuyến hàng chưa cấu hình điểm dừng.</div>');
          return;
        }

        stops.forEach(function (s) {
          const isVisited = s.visited == 1;
          const statusBg = isVisited ? '#dcfce7' : '#fef3c7';
          const statusColor = isVisited ? '#15803d' : '#b45309';
          const statusText = isVisited ? 'Đã hoàn thành' : 'Chờ ghé';

          const mapBtnHtml = (s.lat && s.lng) 
            ? '<a href="https://www.google.com/maps/dir/?api=1&destination=' + s.lat + ',' + s.lng + '" target="_blank" class="dp-btn-map"><i class="fa fa-location-arrow" style="color: #ffffff;"></i> Chỉ đường</a>'
            : '';

          const actionBtnHtml = isVisited 
            ? '<span style="font-size: 12px; color: #16a34a; font-weight: 600;"><i class="fa fa-check-circle"></i> Đã đến nơi</span>'
            : '<button class="dp-btn-complete btn-mark-complete" data-stop-name="' + s.name + '"><i class="fa fa-check"></i> Đánh dấu Đã đến</button>';

          container.append(
            '<div class="dp-stop-card">' +
              '<div style="display: flex; justify-content: space-between; align-items: flex-start;">' +
                '<div>' +
                  '<span style="font-weight: 700; font-size: 14px; color: #111827;">#' + s.idx + '. ' + esc(s.customer || 'Khách hàng') + '</span>' +
                '</div>' +
                '<span class="dp-badge-status" style="background: ' + statusBg + '; color: ' + statusColor + ';">' + statusText + '</span>' +
              '</div>' +
              '<div style="font-size: 12px; color: #4b5563; margin-top: 6px; line-height: 1.4;">' +
                '<i class="fa fa-map-marker" style="color: #6b7280; margin-right: 4px;"></i>' + esc(s.address || 'Chưa cập nhật địa chỉ') +
              '</div>' +
              '<div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px; border-top: 1px solid #f3f4f6; padding-top: 8px;">' +
                mapBtnHtml +
                actionBtnHtml +
              '</div>' +
            '</div>'
          );
        });

        // Đăng ký sự kiện nút Đánh dấu Hoàn thành
        $('.btn-mark-complete').off('click').on('click', function () {
          const stopName = $(this).data('stop-name');
          const btn = $(this);
          btn.prop('disabled', true).text('Đang xử lý...');

          frappe.call({
            method: 'dp_dispatch.dp_dispatch.api.gps.complete_delivery_stop',
            args: { stop_name: stopName },
            callback: function (res) {
              if (res.message && res.message.status === 'success') {
                frappe.show_alert({ message: __('Đã cập nhật trạng thái điểm dừng!'), indicator: 'green' });
                if (res.message.trip_completed) {
                  frappe.msgprint(__('🎉 Chúc mừng! Bạn đã hoàn thành tất cả các điểm dừng trong chuyến hàng!'));
                }
                loadDriverSchedule();
              }
            }
          });
        });
      }
    });
  }

  $('#btn-refresh-driver').on('click', function () {
    loadDriverSchedule();
  });

  loadDriverSchedule();
};
