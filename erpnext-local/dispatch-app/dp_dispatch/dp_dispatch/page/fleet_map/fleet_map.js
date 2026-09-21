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
  loadJs('https://unpkg.com/leaflet@1.9.4/dist/leaflet.js', function() {
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

    const trackLayer = L.layerGroup().addTo(map);
    const routeLayer = L.layerGroup().addTo(map);
    const historyLayer = L.layerGroup().addTo(map);
    
    const markers = {};
    const stopMarkersList = [];
    let vehiclesData = [];
    
    let selectedPlate = null;
    let currentNavIndex = -1;

    function ageMin(t) {
      if (!t) return Infinity;
      const now = moment(frappe.datetime.now_datetime().toString().slice(0, 19)); 
      return now.diff(moment(String(t).slice(0, 19)), 'minutes');
    }

    // Hàm định dạng hiển thị thời gian linh hoạt
    function formatTimeAgo(time) {
      const m = ageMin(time);
      if (!isFinite(m)) return 'Mất tín hiệu';
      if (m < 60) {
        return `${m} phút trước`;
      }
      const hrs = Math.floor(m / 60);
      const mins = m % 60;
      return `${hrs} giờ ${mins} phút trước`;
    }

    function getStatusColor(status, time) {
      const st = String(status || '').toLowerCase();
      if (st.includes('bảo dưỡng') || st.includes('sửa chữa') || st.includes('maintenance')) return '#ea580c';
      if (st.includes('hỏng') || st.includes('sự cố') || st.includes('out of service') || st.includes('breakdown')) return '#dc2626';
      const m = ageMin(time);
      return m < 5 ? '#16a34a' : '#000000';
    }

    function canDrawRoute(v) {
      const st = String(v.status || '').toLowerCase();
      const isAvailable = !st || st.includes('khả dụng') || st.includes('available');
      const isOnline = ageMin(v.time) < 5;
      return isAvailable || isOnline;
    }

    function createTruckIcon(color) {
      return L.divIcon({
        className: 'custom-dp-truck-icon',
        html: `<div class="dp-truck-marker" style="background-color: ${color};"><i class="fa fa-truck" style="color: #ffffff;"></i></div>`,
        iconSize: [32, 32], iconAnchor: [16, 16], popupAnchor: [0, -18]
      });
    }

    function createStopIcon(seq) {
      return L.divIcon({
        className: 'custom-dp-stop-icon',
        html: `<div class="dp-stop-marker" style="color: #ffffff;">${seq}</div>`,
        iconSize: [26, 26], iconAnchor: [13, 13], popupAnchor: [0, -14]
      });
    }

    function getTruckPopupHtml(v) {
      const timeAgoText = formatTimeAgo(v.time);
      const color = getStatusColor(v.status, v.time);
      
      const simBadgeHtml = (v.source_type === 'Simulated') 
        ? `<span class="dp-badge-simulated" style="margin-left: 4px;">Mô phỏng</span>` 
        : '';

      return `
        <div style="padding: 6px 8px; min-width: 220px;">
          <div style="border-bottom: 1px solid #333333; padding-bottom: 8px; margin-bottom: 8px;">
            <div style="color: #ffffff; font-size: 15px; font-weight: 700; margin-bottom: 6px;">
              <i class="fa fa-truck" style="color: #ffffff; margin-right: 6px;"></i>${esc(v.plate)}
            </div>
            <div>
              <span style="background: ${color}; color: #ffffff; font-size: 11px; padding: 3px 8px; border-radius: 6px; font-weight: 600; display: inline-block;"> 
                ${esc(v.status || 'Khả dụng')}
              </span>
              ${simBadgeHtml}
            </div>
          </div>
          <div style="font-size: 12px; color: #d4d4d8; line-height: 1.6;">
            <div>Tín hiệu: <b>${timeAgoText}</b></div>
            <div>Thiết bị: ${esc(v.device || 'N/A')}</div>
            <div>Tọa độ: ${v.lat ? v.lat.toFixed(5) : '0'}, ${v.lng ? v.lng.toFixed(5) : '0'}</div>
          </div>
        </div>`;
    }

    function selectVehicle(plate, preserveView) {
      const v = vehiclesData.find(item => item.plate === plate);
      if (!v) return;

      if (!preserveView) {
        map.closePopup();
      }
      routeLayer.clearLayers();
      trackLayer.clearLayers();
      historyLayer.clearLayers();
      stopMarkersList.length = 0;

      selectedPlate = plate;
      currentNavIndex = -1;

      $('.dp-vehicle-item').removeClass('active');$(`.dp-vehicle-item[data-plate="${plate}"]`).addClass('active');

      const statusColor = getStatusColor(v.status, v.time);
      $('#selected-vehicle-name').text(plate);
      $('#selected-vehicle-tag').css({
        'background-color': statusColor,
        'border-color': statusColor
      }).show();

      $('#vehicle-actions-group').css('display', 'inline-flex');

      if (canDrawRoute(v)) {
        drawRouteFromTruck(plate, v.lat, v.lng);
      } else {
        if (markers[plate] && !preserveView) {
          map.setView([v.lat, v.lng], 15);
          markers[plate].openPopup();
        }
      }
    }

    function loadGpsHistory(plate) {
      historyLayer.clearLayers();
      frappe.call({
        method: 'dp_dispatch.api.gps.get_gps_history',
        args: { vehicle: plate, limit: 200 },
        callback: function(r) {
          if (!r.message || !r.message.length) {
            return frappe.show_alert({ message: __('Không có dữ liệu lịch sử GPS Log'), indicator: 'orange' });
          }
          const pts = r.message.map(p => [p.latitude, p.longitude]);
          const polyline = L.polyline(pts, { color: '#2563eb', weight: 4, opacity: 0.8 }).addTo(historyLayer);
          
          pts.forEach((pt, i) => {
            L.circleMarker(pt, { radius: 4, color: '#1d4ed8', fillColor: '#ffffff', fillOpacity: 1 }).addTo(historyLayer)
              .bindPopup(`<b style="color:#ffffff;"><i class="fa fa-map-marker" style="color:#ffffff; margin-right:4px;"></i>Điểm GPS #${i+1}</b><br>Thời gian: ${r.message[i].recorded_at}<br>Nguồn: ${r.message[i].source_type}`);
          });

          map.fitBounds(polyline.getBounds(), { padding: [50, 50] });
          frappe.show_alert({ message: __('Đã tải {0} điểm lịch sử GPS Log', [r.message.length]), indicator: 'green' });
        }
      });
    }

    function renderVehicleList(filterKeyword) {
      const container = $('#vehicle-list-container');
      container.empty();

      const filtered = vehiclesData.filter(v => {
        if (!filterKeyword) return true;
        return v.plate.toLowerCase().includes(filterKeyword.toLowerCase());
      });

      if (!filtered.length) {
        container.html('<div style="text-align: center; color: #9ca3af; font-size: 11px; padding: 15px;">Không thấy xe</div>');
        return;
      }

      filtered.forEach(v => {
        const color = getStatusColor(v.status, v.time);
        const timeAgoText = formatTimeAgo(v.time);
        const isActive = v.plate === selectedPlate ? 'active' : '';

        const itemHtml = `
          <div class="dp-vehicle-item ${isActive}" data-plate="${esc(v.plate)}">
            <div>
              <div style="font-weight: 700; font-size: 12px;">🚛 ${esc(v.plate)}</div>
              <div class="dp-vehicle-subtext" style="font-size: 10px; color: #6b7280; margin-top: 1px;">
                ${timeAgoText}
              </div>
            </div>
            <span style="background: ${color}; width: 8px; height: 8px; border-radius: 50%; display: inline-block;"></span>
          </div>
        `;
        container.append(itemHtml);
      });
    }

    function upsertVehicle(v) {
      if (!v.lat || !v.lng) return;
      let m = markers[v.plate];
      const color = getStatusColor(v.status, v.time);

      if (!m) {
        m = L.marker([v.lat, v.lng], { icon: createTruckIcon(color) }).addTo(map);
        m.bindPopup(function() { return getTruckPopupHtml(m._dp); });

        m.on('click', function() {
          selectVehicle(v.plate);
        });

        markers[v.plate] = m;
      } else {
        m.setLatLng([v.lat, v.lng]);
        m.setIcon(createTruckIcon(color));
      }
      m._dp = Object.assign(m._dp || {}, v);
    }

    function loadVehicles(isRefresh) {
      return frappe.call({
        method: 'frappe.client.get_list',
        args: {
          doctype: 'Vehicle',
          fields: ['name', 'custom_technical_status', 'custom_gps_device_id', 'custom_last_lat', 'custom_last_lng', 'custom_last_gps_time'],
          limit_page_length: 500
        },
        callback: function(r) {
          if (!r.message) return;
          let online = 0;
          vehiclesData = [];

          const promises = r.message.map(function(row) {
            if (row.custom_last_lat && row.custom_last_lng) {
              const vObj = {
                plate: row.name,
                status: row.custom_technical_status,
                device: row.custom_gps_device_id,
                lat: row.custom_last_lat,
                lng: row.custom_last_lng,
                time: row.custom_last_gps_time,
                source_type: 'Hardware GPS'
              };

              return frappe.db.get_value('GPS Log', { vehicle: row.name }, 'source_type')
                .then(function(res) {
                  if (res && res.message && res.message.source_type) {
                    vObj.source_type = res.message.source_type;
                  }
                  vehiclesData.push(vObj);
                  upsertVehicle(vObj);
                  if (ageMin(row.custom_last_gps_time) < 5) online++;
                });
            }
            return Promise.resolve();
          });

          Promise.all(promises).then(function() {
            $('#stat-total').text(r.message.length + ' xe');
            $('#stat-online').text(online + ' Trực tuyến');
            renderVehicleList($('#vehicle-search').val());

            const pts = Object.values(markers).map(m => m.getLatLng());
            if (pts.length && !loadVehicles.fitted) {
              map.fitBounds(L.latLngBounds(pts), { padding: [80, 80], maxZoom: 13 }); 
              loadVehicles.fitted = true;
            }

            if (isRefresh && selectedPlate) {
              selectVehicle(selectedPlate, true);
            }
          });
        }
      });
    }

    function calcDist(lat1, lon1, lat2, lon2) {
      const R = 6371;
      const dLat = (lat2 - lat1) * Math.PI / 180;
      const dLon = (lon2 - lon1) * Math.PI / 180;
      const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * 
                Math.sin(dLon/2) * Math.sin(dLon/2);
      return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    }

    function optimizeRoute(startLat, startLng, stops) {
      let unvisited = stops.slice();
      let currentLat = startLat;
      let currentLng = startLng;
      let orderedRoute = [];

      while (unvisited.length > 0) {
        let nearestIdx = 0;
        let minD = Infinity;

        for (let i = 0; i < unvisited.length; i++) {
          let d = calcDist(currentLat, currentLng, unvisited[i].lat, unvisited[i].lng);
          if (d < minD) {
            minD = d;
            nearestIdx = i;
          }
        }

        let nextStop = unvisited.splice(nearestIdx, 1)[0];
        currentLat = nextStop.lat;
        currentLng = nextStop.lng;
        orderedRoute.push(nextStop);
      }
      return orderedRoute;
    }

    function drawRouteFromTruck(plate, truckLat, truckLng) {
      routeLayer.clearLayers();
      stopMarkersList.length = 0;

      frappe.db.get_list('Delivery Trip', {
        filters: { vehicle: plate, docstatus: ['<', 2] },
        fields: ['name', 'driver_name', 'departure_time'],
        order_by: 'creation desc',
        limit: 1
      }).then(function(trips) {
        if (!trips || !trips.length) {
          if (markers[plate]) {
            map.setView([truckLat, truckLng], 15);
          }
          return frappe.show_alert({ message: __('Xe {0} chưa có chuyến giao hàng active', [plate]), indicator: 'orange' });
        }

        const trip = trips[0];
        frappe.db.get_list('Delivery Stop', {
          parent_doctype: 'Delivery Trip',
          filters: { parent: trip.name },
          fields: ['idx', 'customer', 'lat', 'lng', 'address'],
          limit: 100
        }).then(function(stops) {
          const validStops = stops.filter(s => s.lat && s.lng);
          if (!validStops.length) {
            if (markers[plate]) {
              map.setView([truckLat, truckLng], 15);
            }
            return frappe.show_alert({ message: __('Chuyến {0} chưa có tọa độ điểm giao hàng', [trip.name]), indicator: 'orange' });
          }

          const sortedStops = optimizeRoute(truckLat, truckLng, validStops);
          const path = [[truckLat, truckLng]].concat(sortedStops.map(s => [s.lat, s.lng]));
          const polyline = L.polyline(path, { color: '#18181b', weight: 4, dashArray: '6, 6', opacity: 0.85 }).addTo(routeLayer);

          sortedStops.forEach(function(s, seq) {
            const seqNum = seq + 1;
            const sm = L.marker([s.lat, s.lng], { icon: createStopIcon(seqNum) }).addTo(routeLayer)
              .bindPopup(`
                <div style="padding: 4px; min-width: 180px;">
                  <b style="color: #ffffff; font-size: 13px;">
                    <i class="fa fa-map-marker" style="color: #ffffff; margin-right: 6px;"></i>Điểm ghé #${seqNum}
                  </b>
                  <div style="font-size: 11px; color: #d4d4d8; margin-top: 4px;"> 
                    <div>Khách hàng: <b>${esc(s.customer || 'N/A')}</b></div>
                    <div>Địa chỉ: ${esc(s.address || 'N/A')}</div>
                  </div>
                </div>
              `);
            stopMarkersList.push(sm);
          });

          map.fitBounds(polyline.getBounds(), { padding: [80, 80], maxZoom: 14 });
        });
      });
    }

    $(document).on('click', '.dp-vehicle-item', function() {
      const plate = $(this).data('plate');
      selectVehicle(plate);
    });

    $('#vehicle-search').on('input', function() {
      renderVehicleList($(this).val());
    });

    $('#btn-zoom-truck').on('click', function() {
      if (selectedPlate && markers[selectedPlate]) {
        currentNavIndex = -1;
        const m = markers[selectedPlate];
        map.setView(m.getLatLng(), 15);
        m.openPopup();
      }
    });

    $('#btn-view-history').on('click', function() {
      if (selectedPlate) {
        loadGpsHistory(selectedPlate);
      }
    });

    $('#btn-zoom-next').on('click', function() {
      if (!stopMarkersList.length) {
        return frappe.show_alert({ message: __('Xe chưa có điểm giao hàng active'), indicator: 'orange' });
      }
      if (currentNavIndex < stopMarkersList.length - 1) {
        currentNavIndex++;
      }
      const sm = stopMarkersList[currentNavIndex];
      if (sm) {
        map.setView(sm.getLatLng(), 15);
        sm.openPopup();
      }
    });

    $('#btn-zoom-prev').on('click', function() {
      if (!stopMarkersList.length) {
        return frappe.show_alert({ message: __('Xe chưa có điểm giao hàng active'), indicator: 'orange' });
      }
      if (currentNavIndex > 0) {
        currentNavIndex--;
        const sm = stopMarkersList[currentNavIndex];
        if (sm) {
          map.setView(sm.getLatLng(), 15);
          sm.openPopup();
        }
      } else {
        currentNavIndex = -1;
        if (selectedPlate && markers[selectedPlate]) {
          const m = markers[selectedPlate];
          map.setView(m.getLatLng(), 15);
          m.openPopup();
        }
      }
    });

    $('#btn-hide-info').on('click', function() {
      map.closePopup();
      trackLayer.clearLayers();
      routeLayer.clearLayers();
      historyLayer.clearLayers();
      selectedPlate = null;
      currentNavIndex = -1;
      stopMarkersList.length = 0;
      $('.dp-vehicle-item').removeClass('active');$('#selected-vehicle-tag').hide();
      $('#vehicle-actions-group').hide();
    });

    $('#btn-refresh').on('click', function() {
      loadVehicles(true);
    });

    loadVehicles(false);
  });
};
