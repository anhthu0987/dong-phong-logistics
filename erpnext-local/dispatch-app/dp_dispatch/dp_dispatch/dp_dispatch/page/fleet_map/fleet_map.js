frappe.pages["fleet-map"].on_page_load = function(wrapper) {
  var page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "Fleet Map",
    single_column: true
  });

  $(wrapper).find(".layout-main-section").html(`
    <div style="display:flex; height: 80vh; gap: 15px;">
      <div style="width: 300px; border-right: 1px solid #d1d8dd; padding-right: 15px; display:flex; flex-direction:column;">
        <div style="margin-bottom: 10px;">
          <h4 id="stat-total" style="margin:0;">0 Vehicles</h4>
          <small id="stat-online" style="color: green;">0 Active</small>
        </div>
        <div id="vehicle-list-container" style="flex:1; overflow-y:auto;"></div>
      </div>
      <div id="map" style="flex:1; height: 100%; border-radius: 8px;"></div>
    </div>
  `);

  var map = L.map("map").setView([16.0544, 108.2022], 12);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "© OpenStreetMap"
  }).addTo(map);

  var markers = {};

  function loadVehicles() {
    frappe.call({
      method: "frappe.client.get_list",
      args: {
        doctype: "Vehicle",
        fields: ["name", "custom_last_lat", "custom_last_lng", "custom_last_gps_time"]
      },
      callback: function(r) {
        if (!r.message) return;
        let online = 0;
        let listHtml = "";

        r.message.forEach(function(row) {
          if (row.custom_last_lat && row.custom_last_lng) {
            online++;
            let lat = parseFloat(row.custom_last_lat);
            let lng = parseFloat(row.custom_last_lng);

            if (markers[row.name]) {
              markers[row.name].setLatLng([lat, lng]);
            } else {
              markers[row.name] = L.marker([lat, lng])
                .addTo(map)
                .bindPopup("<b>" + row.name + "</b><br>Last seen: " + (row.custom_last_gps_time || "N/A"));
            }

            listHtml += `
              <div style="padding: 10px; border-bottom: 1px solid #eee; cursor: pointer;" onclick="window.focusVehicle('` + row.name + `', ` + lat + `, ` + lng + `)">
                <strong>` + row.name + `</strong><br>
                <small>` + (row.custom_last_gps_time || "") + `</small>
              </div>
            `;
          }
        });

        $("#stat-total").text(r.message.length + " Vehicles");
        $("#stat-online").text(online + " Active");
        $("#vehicle-list-container").html(listHtml);
      }
    });
  }

  window.focusVehicle = function(vehicle, lat, lng) {
    map.setView([lat, lng], 15);
    if (markers[vehicle]) markers[vehicle].openPopup();
  };

  loadVehicles();
  setInterval(loadVehicles, 5000);
};