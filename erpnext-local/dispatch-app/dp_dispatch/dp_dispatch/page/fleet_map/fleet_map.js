frappe.pages['fleet-map'].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __('Fleet map'),
    single_column: true
  });

  $(wrapper).find('.page-content').css({ 'padding': '0', 'margin': '0' });$(wrapper).find('.page-head').css({ 'margin-bottom': '2px', 'padding': '6px 15px' });

  $(page.main).html(`
    <style>
      .dp-container {
        padding-bottom: 8px;
        font-family: var(--font-stack, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif);
      }
      .dp-header-bar {
        background: #ffffff;
        color: #111827;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 8px;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      }
      .dp-btn-black {
        background: #000000;
        color: #ffffff;
        border: 1px solid #000000;
        font-size: 12px;
        font-weight: 600;
        padding: 6px 12px;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.2s ease;
      }
      .dp-btn-black:hover { background: #262626; border-color: #262626; color: #ffffff; }
      .dp-btn-outline-black {
        background: #ffffff;
        color: #000000;
        border: 1px solid #000000;
        font-size: 12px;
        font-weight: 600;
        padding: 6px 12px;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.2s ease;
      }
      .dp-btn-outline-black:hover { background: #f4f4f5; color: #000000; }

      .dp-badge-bw {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        background: #f4f4f5;
        color: #18181b;
        border: 1px solid #e4e4e7;
      }

      .dp-badge-simulated {
        background: #fef3c7;
        color: #92400e;
        border: 1px solid #fde68a;
        font-size: 11px;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: 700;
        display: inline-block;
      }

      .dp-main-layout {
        display: flex;
        gap: 8px;
        height: calc(100dvh - 186px);
        min-height: 520px;
      }

      .dp-sidebar {
        width: 205px;
        min-width: 205px;
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
      }
      .dp-sidebar-header {
        padding: 8px;
        background: #f9fafb;
        border-bottom: 1px solid #e5e7eb;
      }
      
      .dp-search-box {
        position: relative;
        display: flex;
        align-items: center;
      }
      .dp-search-icon {
        position: absolute;
        left: 8px;
        color: #000000;
        font-size: 11px;
        pointer-events: none;
      }
      .dp-search-input {
        width: 100%;
        padding: 5px 8px 5px 26px;
        font-size: 11px;
        border: 1px solid #e5e7eb;
        border-radius: 6px;
        outline: none;
        background: #ffffff;
        color: #000000;
      }
      .dp-search-input:focus { border-color: #000000; }

      .dp-vehicle-list {
        flex: 1;
        overflow-y: auto;
        padding: 4px;
      }
      .dp-vehicle-item {
        padding: 6px 8px;
        border-radius: 6px;
        border: 1px solid transparent;
        margin-bottom: 3px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: all 0.15s ease;
      }
      .dp-vehicle-item:hover { background: #f4f4f5; }
      .dp-vehicle-item.active { background: #000000; color: #ffffff; }
      .dp-vehicle-item.active .dp-vehicle-subtext { color: #a1a1aa; }

      .dp-truck-marker {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        color: #ffffff;
        font-size: 14px;
        border: 2px solid #ffffff;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      }

      .dp-stop-marker {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 26px;
        height: 26px;
        border-radius: 50%;
        background: #000000;
        color: #ffffff;
        font-size: 12px;
        font-weight: 700;
        border: 2px solid #ffffff;
        box-shadow: 0 2px 5px rgba(0,0,0,0.3);
      }

      .leaflet-control-zoom {
        border: 1px solid #000000 !important;
        border-radius: 6px !important;
        overflow: hidden;
        box-shadow: 0 2px 6px rgba(0,0,0,0.15) !important;
      }
      .leaflet-control-zoom-in, .leaflet-control-zoom-out {
        background-color: #ffffff !important;
        color: #000000 !important;
        border-bottom: 1px solid #e5e7eb !important;
        font-weight: 700 !important;
        transition: all 0.15s ease;
      }
      .leaflet-control-zoom-in:hover, .leaflet-control-zoom-out:hover {
        background-color: #000000 !important;
        color: #ffffff !important;
      }

      .leaflet-popup-content-wrapper {
        background: #000000 !important;
        color: #ffffff !important;
        border-radius: 8px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.25);
        font-family: var(--font-stack, sans-serif);
      }
      .leaflet-popup-tip { background: #000000 !important; }
    </style>

    <div class="dp-container">
      <div class="dp-header-bar">
        <div style="display: flex; align-items: center; gap: 8px;">
          <button id="btn-refresh" class="dp-btn-black">
            <i class="fa fa-refresh" style="margin-right: 4px;"></i> Làm mới
          </button>
          
          <div id="vehicle-actions-group" style="display: none; align-items: center; gap: 8px;">
            <button id="btn-zoom-truck" class="dp-btn-outline-black">
              <i class="fa fa-search-plus" style="margin-right: 4px;"></i> Zoom Xe
            </button>
            <button id="btn-view-history" class="dp-btn-outline-black">
              <i class="fa fa-history" style="margin-right: 4px;"></i> Lịch sử GPS
            </button>
            <button id="btn-zoom-prev" class="dp-btn-outline-black">
              <i class="fa fa-arrow-left" style="margin-right: 4px;"></i> Zoom Điểm Trước
            </button>
            <button id="btn-zoom-next" class="dp-btn-outline-black">
              <i class="fa fa-arrow-right" style="margin-right: 4px;"></i> Zoom Điểm Kế
            </button>
            <button id="btn-hide-info" class="dp-btn-outline-black" style="color: #ef4444; border-color: #ef4444;">
              <i class="fa fa-eye-slash" style="margin-right: 4px;"></i> Ẩn thông tin
            </button>
          </div>
        </div>

        <div style="display: flex; align-items: center; gap: 10px;">
          <span id="selected-vehicle-tag" class="dp-badge-bw" style="display: none; color: #ffffff; transition: all 0.3s ease;">
            <i class="fa fa-truck" style="color: #ffffff; margin-right: 2px;"></i> <span id="selected-vehicle-name">--</span>
          </span>
          <span class="dp-badge-bw">
            <i class="fa fa-truck"></i> <span id="stat-total">0 xe</span>
          </span>
          <span class="dp-badge-bw">
            <i class="fa fa-circle" style="font-size: 8px; color: #16a34a;"></i> <span id="stat-online">0 Trực tuyến</span>
          </span>
        </div>
      </div>

      <div class="dp-main-layout">
        <div class="dp-sidebar">
          <div class="dp-sidebar-header">
            <div class="dp-search-box">
              <i class="fa fa-search dp-search-icon"></i>
              <input type="text" id="vehicle-search" class="dp-search-input" placeholder="Tìm biển số xe..." />
            </div>
          </div>
          <div id="vehicle-list-container" class="dp-vehicle-list">
            <div style="text-align: center; color: #9ca3af; font-size: 11px; padding: 15px;">Đang tải...</div>
          </div>
        </div>

        <div id="dp-map" style="flex: 1; height: 100%; border-radius: 8px; border: 1px solid #e5e7eb; z-index: 1;"></div>
      </div>
    </div>
  `);

  const esc = frappe.utils.escape_html;

  function loadCss(url) {
    if (!document.querySelector('link[href*="leaflet.css"]')) {
      const link = document.createElement('link'); link.rel = 'stylesheet'; link.href = url; document.head.appendChild(link);
    }
  }

  function loadJs(url, callback) {
    if (window.L) { callback(); return; }
    const script = document.createElement('script'); script.src = url; script.onload = callback; document.head.appendChild(script);
  }

  loadCss('https://unpkg.com/leaflet@1.9.4/dist/leaflet.css');
  loadJs('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js', async function() {
    const map = L.map('dp-map', {
      zoomControl: false,
      minZoom: 2,
      maxZoom: 19
    }).setView([10.85, 106.75], 9);

    L.control.zoom({ position: 'topright' }).addTo(map);

    const mapLang = (frappe.boot && frappe.boot.lang) ? frappe.boot.lang : 'vi';

    L.tileLayer(`https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}&hl=${mapLang}`, {
      minZoom: 2,
      maxZoom: 19,
      noWrap: true,
      attribution: '&copy; Google Maps'
    }).addTo(map);

    setTimeout(function() { map.invalidateSize(); }, 300);


    const routeLayer = L.layerGroup().addTo(map);
    const historyLayer = L.layerGroup().addTo(map);
    const positionLayer = L.layerGroup().addTo(map);
    const controls = $('<div class="form-group" style="padding:12px"><label>Chuyến vận chuyển</label><select class="form-control dp-map-trip"></select><div class="dp-map-status text-muted" style="margin-top:8px"></div></div>').prependTo(page.main);
    const selector = controls.find('select');
    let selected = null, generation = 0, polling = false, positionMarker = null;
    let stopMarkers = [], nav = -1, trips = [];
    function coord(p) { return p && p.lat != null && p.lng != null; }
    function status(text) { controls.find('.dp-map-status').text(text); }
    function renderTrips(keyword = '') {
      const list = $(page.main).find('#vehicle-list-container').empty();
      trips.filter(t => `${t.name} ${t.vehicle}`.toLowerCase().includes(keyword.toLowerCase())).forEach(t => {
        $('<button class="btn btn-default" style="display:block;width:100%;margin:4px 0;text-align:left">')
          .text(`${t.vehicle || 'Chưa gán xe'} · ${t.name} · ${t.status}`)
          .on('click', () => choose(t.name)).appendTo(list);
      });
    }
    async function draw(fit = false) {
      if (!selected) return;
      const tripName = selected, token = generation;
      const {message:data} = await frappe.call({method:'dp_dispatch.tracking.get_trip_tracking',args:{delivery_trip:tripName}});
      if (token !== generation || selected !== tripName) return;
      routeLayer.clearLayers(); positionLayer.clearLayers(); stopMarkers=[]; positionMarker=null;
      const points = [], missing = [];
      const path = [];
      if (data.trip.custom_origin_lat || data.trip.custom_origin_lng) path.push([data.trip.custom_origin_lat,data.trip.custom_origin_lng]);
      data.stops.forEach(s => {
        if (!coord(s)) {missing.push(s.idx); return;}
        const pt = [s.lat,s.lng]; points.push(pt); path.push(pt);
        const kind = {Pickup:'Lấy hàng',Delivery:'Giao hàng',Return:'Trả người gửi'}[s.operation] || s.operation;
        const marker = L.marker(pt).addTo(routeLayer).bindPopup(`<b>#${s.idx} ${esc(kind)}</b><br>${esc(s.customer || '')}<br>${esc(s.address || '')}<br>${esc(s.status || '')}`);
        stopMarkers.push(marker);
      });
      // This is a schematic in approved stop order, never a road-routing/optimization result.
      if (path.length > 1 && !missing.length) L.polyline(path,{color:'#18181b',dashArray:'6 6',weight:3}).addTo(routeLayer);
      const p = data.position;
      let positionText = 'Chưa có GPS cho chuyến này';
      if (p) {
        const age = moment(frappe.datetime.now_datetime()).diff(moment(String(p.recorded_at)), 'minutes');
        const stale = age >= 5 || data.trip.status !== 'In Transit';
        positionText = `GPS cuối: ${p.recorded_at}${stale ? ' — dữ liệu cũ / chuyến không chạy' : ''}`;
        const pt=[p.latitude,p.longitude]; points.push(pt);
        positionMarker=L.circleMarker(pt,{radius:9,color:stale?'#6b7280':'#16a34a',fillOpacity:0.9}).addTo(positionLayer)
          .bindPopup(`${esc(data.trip.vehicle || '')}<br>${esc(positionText)}<br>${esc(p.source_type || '')}`);
      }
      status(`${data.trip.name} · ${data.trip.status} · ${positionText}. Nét đứt: sơ đồ thứ tự điểm, chưa phải đường chạy thực tế.${missing.length ? ' Thiếu tọa độ điểm: '+missing.join(', ')+'.' : ''}`);
      $('#selected-vehicle-name',page.main).text(`${data.trip.vehicle} · ${tripName}`);
      $('#selected-vehicle-tag,#vehicle-actions-group',page.main).show();
      $('#stat-online',page.main).text(data.trip.status === 'In Transit' ? 'Đang thực hiện' : data.trip.status);
      if (fit && points.length) map.fitBounds(L.latLngBounds(points),{padding:[40,40],maxZoom:14});
    }
    async function choose(name) {
      generation++;
      selected=name; nav=-1; selector.val(name);
      historyLayer.clearLayers(); routeLayer.clearLayers(); positionLayer.clearLayers();
      stopMarkers=[]; positionMarker=null;
      await draw(true);
    }
    async function refresh() {
      const {message:rows} = await frappe.call({method:'dp_dispatch.tracking.list_trips'});
      trips=rows || [];
      selector.empty();
      trips.forEach(t => $('<option>').val(t.name).text(`${t.name} · ${t.vehicle || ''} · ${t.status}`).appendTo(selector));
      renderTrips($('#vehicle-search',page.main).val() || '');
      $('#stat-total',page.main).text(`${trips.length} chuyến`);
      const requested=frappe.route_options?.delivery_trip;
      if (requested) frappe.route_options=null;
      const target=requested || selected || trips.find(t => t.status==='In Transit')?.name || trips[0]?.name;
      if (target) {
        // Explicit links are permission-checked by the backend even beyond the list's page limit.
        if (!trips.some(t => t.name===target)) $('<option>').val(target).text(target).appendTo(selector);
        await choose(target);
      } else { status('Chưa có chuyến đã Submit trong phạm vi được xem.'); }
    }
    selector.on('change',function(){choose(this.value);});
    $('#vehicle-search',page.main).attr('placeholder','Tìm xe hoặc chuyến...').on('input',function(){renderTrips(this.value);});
    $('#btn-view-history',page.main).on('click',async function(){
      if (!selected) return;
      const trip=selected, token=generation;
      const {message:rows}=await frappe.call({method:'dp_dispatch.dp_dispatch.api.gps.get_gps_history',args:{delivery_trip:trip,limit:3000}});
      if (token!==generation || trip!==selected) return;
      historyLayer.clearLayers();
      if (!rows?.length) return frappe.msgprint('Chuyến này chưa có lịch sử GPS.');
      const pts=rows.map(p=>[p.latitude,p.longitude]);
      L.polyline(pts,{color:'#2563eb',weight:4}).addTo(historyLayer);
      rows.forEach(p=>L.circleMarker([p.latitude,p.longitude],{radius:3}).addTo(historyLayer).bindPopup(esc(String(p.recorded_at))));
      map.fitBounds(L.latLngBounds(pts),{padding:[40,40],maxZoom:16});
    });
    $('#btn-zoom-truck',page.main).on('click',()=>{if(positionMarker){map.setView(positionMarker.getLatLng(),16);positionMarker.openPopup();}});
    function navigate(delta) {
      if (!stopMarkers.length) return;
      nav=Math.max(0,Math.min(stopMarkers.length-1,nav+delta));
      map.setView(stopMarkers[nav].getLatLng(),16); stopMarkers[nav].openPopup();
    }
    $('#btn-zoom-next',page.main).on('click',()=>navigate(1));
    $('#btn-zoom-prev',page.main).on('click',()=>navigate(-1));
    $('#btn-hide-info',page.main).on('click',()=>{map.closePopup();historyLayer.clearLayers();});
    $('#btn-refresh',page.main).on('click',refresh);
    wrapper.dp_refresh=refresh;
    const timer=setInterval(async()=>{
      if (!document.body.contains(wrapper)) {clearInterval(timer);return;}
      if (polling || document.hidden || !$(wrapper).is(':visible') || !selected) return;
      polling=true;
      try {await draw();} catch (_) {status('Không tải được GPS. Hãy kiểm tra kết nối và bấm cập nhật.');}
      finally {polling=false;}
    },3000);
    await refresh();
  });
};
frappe.pages['fleet-map'].on_page_show = function(wrapper) {return wrapper.dp_refresh?.();};
