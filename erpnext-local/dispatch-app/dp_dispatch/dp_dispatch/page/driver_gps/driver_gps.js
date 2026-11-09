frappe.pages['driver-gps'].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({parent: wrapper, title: __('Lịch trình tài xế'), single_column: true});
  const esc = value => frappe.utils.escape_html(String(value ?? ''));
  const main = $(page.main).html(`<div style="max-width:800px;margin:auto">
    <div class="form-group"><label>Chuyến được phân công</label><select class="form-control dp-trip-select"></select></div>
    <div class="dp-trip-summary"></div><div class="dp-trip-actions" style="display:flex;gap:8px;flex-wrap:wrap;margin:16px 0"></div>
    <div class="dp-stops"></div></div>`);
  let selected = null, serial = 0;
  const kinds = {Pickup:'Lấy hàng', Delivery:'Giao hàng', Return:'Trả người gửi'};
  const states = {'Picked Up':'Đã lấy hàng', Delivered:'Đã giao', Partial:'Giao một phần', Returned:'Đã trả', Assigned:'Chờ thực hiện', Exception:'Sự cố'};
  function button(label, action) {
    return $('<button class="btn btn-default btn-sm">').text(label).on('click', action);
  }
  async function run(action, args = {}) {
    await frappe.call({method:'dp_dispatch.completion.' + action, args:{trip:selected, ...args}, freeze:true});
    await load();
  }
  async function load() {
    const request = ++serial;
    const {message:data} = await frappe.call({method:'dp_dispatch.dp_dispatch.api.gps.get_driver_schedule', args:{delivery_trip:selected}});
    if (request !== serial) return;
    const select = main.find('.dp-trip-select').empty();
    const trips = data.trips || [];
    if (data.trip && !trips.some(t => t.name === data.trip.name)) trips.unshift(data.trip);
    trips.forEach(t => $('<option>').val(t.name).text(`${t.name} · ${t.vehicle || ''} · ${t.status}`).appendTo(select));
    const actions = main.find('.dp-trip-actions').empty();
    const cards = main.find('.dp-stops').empty();
    if (!data.trip) {
      selected = null;
      main.find('.dp-trip-summary').text('Chưa có chuyến đã Submit được phân công.');
      return;
    }
    const trip = data.trip;
    selected = trip.name;
    select.val(selected);
    main.find('.dp-trip-summary').html(`<h3>${esc(trip.name)}</h3><p>${esc(trip.vehicle)} · ${esc(trip.status)} · Duyệt: ${esc(trip.custom_completion_status || 'Open')}</p>
      <p>Hàng trên xe: <b>${esc(trip.custom_onboard_quantity || '0')}</b> · ${esc(trip.custom_onboard_weight_kg || 0)} kg</p>`);
    actions.append(button('Mở phiếu chuyến', () => frappe.set_route('Form','Delivery Trip',selected)));
    actions.append(button('Bản đồ chuyến', () => {frappe.route_options={delivery_trip:selected}; frappe.set_route('fleet-map');}));
    if (trip.status === 'Scheduled') actions.append(button('Bắt đầu chuyến', () => frappe.confirm('Xác nhận bắt đầu chuyến?', () => run('start_trip'))));
    if (trip.status === 'In Transit' && !['Requested','Approved','Exception Requested','Exception Closed'].includes(trip.custom_completion_status)) {
      actions.append(button('Gửi yêu cầu hoàn tất', () => frappe.confirm('Gửi Admin duyệt sau khi đã xử lý hàng và thu đủ cước?', () => run('request_completion'))));
      actions.append(button('Báo sự cố', () => frappe.prompt([{fieldname:'note',fieldtype:'Small Text',label:'Mô tả sự cố',reqd:1}], values => run('request_incident_closure',values))));
    }
    for (const stop of data.stops) {
      const q = stop.quantities || {};
      const card = $('<div class="frappe-card" style="padding:16px;margin-bottom:12px">').appendTo(cards);
      card.html(`<h4>${esc(stop.idx)}. ${esc(kinds[stop.operation] || stop.operation)} · ${esc(stop.customer)}</h4>
        <p>${esc(stop.address)}</p><p>Đơn: ${esc(stop.order)} · ${esc(states[stop.status] || stop.status)}</p>
        <p>Khung giờ: ${esc(stop.window_start || '—')} → ${esc(stop.window_end || '—')}</p>
        <p>Đã lấy: ${esc(q.picked_up || 0)} · Đã giao: ${esc(q.delivered || 0)} · Đã trả: ${esc(q.returned_to_sender || 0)} · Còn chờ: ${esc(q.pending || 0)}</p>`);
      const controls = $('<div style="display:flex;gap:8px;flex-wrap:wrap">').appendTo(card);
      if (stop.lat != null && stop.lng != null) $('<a class="btn btn-default btn-sm" target="_blank" rel="noopener">')
        .attr('href',`https://www.google.com/maps/dir/?api=1&destination=${stop.lat},${stop.lng}`).text('Chỉ đường').appendTo(controls);
      const submitted = stop.confirmations.find(c => c.docstatus === 1);
      const draft = stop.confirmations.find(c => c.docstatus === 0);
      if (submitted || draft) {
        const doc = submitted || draft;
        controls.append(button(submitted ? 'Xem phiếu giao nhận' : 'Tiếp tục phiếu đang nhập', () => frappe.set_route('Form','Delivery Confirmation',doc.name)));
      } else if (trip.status === 'In Transit' && !trip.custom_completed_at) {
        controls.append(button('Ghi nhận ' + (kinds[stop.operation] || 'giao nhận').toLowerCase(), () =>
          frappe.new_doc('Delivery Confirmation',{delivery_trip:trip.name,delivery_stop:stop.name})));
      }
    }
  }
  main.find('.dp-trip-select').on('change', function () {selected=this.value; load();});
  page.set_secondary_action('Cập nhật', load);
  wrapper.dp_refresh = () => {
    if (frappe.route_options?.delivery_trip) {selected=frappe.route_options.delivery_trip; frappe.route_options=null;}
    return load();
  };
};
frappe.pages['driver-gps'].on_page_show = function (wrapper) { return wrapper.dp_refresh?.(); };
