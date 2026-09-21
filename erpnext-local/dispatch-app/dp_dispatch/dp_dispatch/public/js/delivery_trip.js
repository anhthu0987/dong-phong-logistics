frappe.provide('dp_gps');

dp_gps.load_leaflet = function () {
  const CSS = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
  const JS = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
  if (!document.querySelector('link[href="' + CSS + '"]')) {
    const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = CSS; document.head.appendChild(l);
  }
  return new Promise((resolve, reject) => {
    if (window.L) return resolve();
    const s = document.createElement('script'); s.src = JS; s.onload = resolve; s.onerror = reject;
    document.head.appendChild(s);
  });
};

dp_gps.show_trip_map = async function (frm) {
  try { await dp_gps.load_leaflet(); } catch (e) { return frappe.msgprint(__('Cannot load Leaflet')); }
  const esc = frappe.utils.escape_html;
  const stops = (frm.doc.delivery_stops || []).filter(s => s.lat && s.lng);
  const hasOrigin = frm.doc.custom_origin_lat && frm.doc.custom_origin_lng;
  const track = await frappe.db.get_list('GPS Location Log', {
    filters: { delivery_trip: frm.doc.name }, fields: ['latitude', 'longitude'],
    order_by: 'recorded_at asc', limit: 3000 });
  let veh = null;
  if (frm.doc.vehicle) {
    const r = await frappe.db.get_value('Vehicle', frm.doc.vehicle,
      ['custom_last_lat', 'custom_last_lng', 'custom_last_gps_time']);
    veh = r.message;
  }
  if (!stops.length && !track.length) return frappe.msgprint(__('This trip has no coordinates yet'));

  const d = new frappe.ui.Dialog({
    title: __('Trip map: {0}', [frm.doc.name]), size: 'extra-large',
    fields: [{ fieldtype: 'HTML', fieldname: 'map_html' }] });
  d.fields_dict.map_html.$wrapper.html(
    '<div id="dp-trip-map" style="height:60vh;min-height:360px;border-radius:8px"></div>' +
    '<div class="text-muted small" style="margin-top:6px">' +
    __('Dashed red: planned route') + ' · ' + __('Blue: GPS track') + ' · ' + __('Green dot: last vehicle position') +
    '</div>');
  d.show();

  setTimeout(() => {
    const map = L.map('dp-trip-map');
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      { maxZoom: 19, attribution: '&copy; OpenStreetMap contributors' }).addTo(map);
    const all = [];
    const o = hasOrigin ? [frm.doc.custom_origin_lat, frm.doc.custom_origin_lng] : null;
    const path = (o ? [o] : []).concat(stops.map(s => [s.lat, s.lng]), o ? [o] : []);
    if (path.length > 1) {
      L.polyline(path, { color: '#dc2626', weight: 3, dashArray: '6 6' }).addTo(map);
      path.forEach(p => all.push(p));
    }
    if (o) L.marker(o).addTo(map).bindPopup(__('Depot'));
    stops.forEach(s => L.marker([s.lat, s.lng]).addTo(map).bindPopup(
      '#' + s.idx + ' ' + esc(s.customer || '') +
      (s.estimated_arrival ? '<br>ETA: ' + esc(String(s.estimated_arrival)) : '')));
    if (track.length > 1) {
      const pts = track.map(p => [p.latitude, p.longitude]);
      L.polyline(pts, { color: '#2563eb', weight: 4 }).addTo(map);
      pts.forEach(p => all.push(p));
    }
    if (veh && veh.custom_last_lat && veh.custom_last_lng) {
      const p = [veh.custom_last_lat, veh.custom_last_lng];
      L.circleMarker(p, { radius: 9, weight: 2, color: '#111', fillColor: '#16a34a', fillOpacity: 0.9 })
        .addTo(map).bindPopup(esc(frm.doc.vehicle) + '<br>' + esc(String(veh.custom_last_gps_time || '')));
      all.push(p);
    }
    map.invalidateSize();
    map.fitBounds(L.latLngBounds(all), { padding: [30, 30] });
  }, 300);
};

// Form Trigger
frappe.ui.form.on('Delivery Trip', {
  refresh(frm) {
    if (frm.is_new()) return;
    frm.add_custom_button(__('View Map'), () => dp_gps.show_trip_map(frm), __('GPS'));
    frm.add_custom_button(__('Fleet Map'), () => frappe.set_route('fleet-map'), __('GPS'));
  }
});

// List Trigger
frappe.listview_settings['Delivery Trip'] = frappe.listview_settings['Delivery Trip'] || {};
(function () {
  const settings = frappe.listview_settings['Delivery Trip'];
  const previous = settings.onload;
  settings.onload = function (listview) {
    if (previous) previous(listview);
    listview.page.add_inner_button(__('Fleet Map'), () => frappe.set_route('fleet-map'));
  };
})();