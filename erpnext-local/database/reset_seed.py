"""Dong Phong - Fleet / Dispatch Data Reset & Seeder Script (SNAPSHOT).

Công dụng:
  - Xóa sạch dữ liệu thử nghiệm cũ (Delivery Trip, Delivery Stop, GPS Log).
  - Tái tạo dữ liệu mẫu chuẩn Đông Phong (Depot, Vehicles, Drivers, Customers, Addresses, Trips).
  - GHI ĐÈ 2 user (luôn đưa về đúng trạng thái snapshot, tạo mới nếu chưa có):
      * gps.simulator@dongphong.local  (API key/secret cố định)
      * binh.driver@dongphong.local    (tài xế Trần Minh Bình, xe 51C-234.56)
    Mỗi lần chạy: đặt lại mật khẩu, role, trạng thái enabled, API key, quyền doctype,
    quyền truy cập page và User Permission.
  - Khởi tạo snapshot tọa độ GPS ban đầu cho các xe.

Chạy (từ WSL):
  docker cp erpnext-local/database/reset_seed.py \
    logistics-erpnext-backend-1:/home/frappe/frappe-bench/apps/dp_dispatch/dp_dispatch/reset_seed.py
  docker exec -it logistics-erpnext-backend-1 bench --site logistics.localhost \
    execute dp_dispatch.reset_seed.reset_all_data
"""

import math
import frappe
from frappe.utils import add_days, add_to_date, get_datetime, now_datetime, today
from frappe.utils.password import update_password

COMPANY = 'Công ty Phân phối Đông Phong'
DEPOT = dict(name='Kho trung tâm Đông Phong (mô phỏng)', lat=10.8670, lng=106.6410)

ROAD_FACTOR = 1.25
AVG_SPEED_KMH = 35
STOP_SERVICE_MIN = 25

VEHICLES = [
    ('51C-123.45', 'Isuzu', 'QKR', 1500, 'Diesel', 25000, 'Available'),
    ('51C-234.56', 'Isuzu', 'QKR', 1900, 'Diesel', 18000, 'Available'),
]

DRIVERS = [
    ('Nguyễn Văn An', '0901234567', '790123456701'),
    ('Trần Minh Bình', '0902345678', '790123456702'),
]

STOPS = [
    dict(title='DP DEMO - Điểm giao Bình Dương', line1='Điểm giao mô phỏng của nhóm Đông Phong',
         county='Thủ Dầu Một', city='Thủ Dầu Một', state='Bình Dương', pincode='75000', lat=10.9804, lng=106.6519),
    dict(title='DP DEMO - Điểm giao Thủ Đức', line1='12 Võ Văn Ngân, P. Linh Chiểu',
         county='Thủ Đức', city='TP. Hồ Chí Minh', state='TP. Hồ Chí Minh', pincode='71300', lat=10.8500, lng=106.7650),
]

TRIPS = [
    (-1, '51C-123.45', 0, 8, [0, 1], 900, True),
    (0, '51C-234.56', 1, 8, [0], 1100, False),
]

DEFAULT_CUSTOMER_GROUP = 'Commercial'
DEFAULT_TERRITORY = 'Vietnam'

# ----------------------------------------------------------------------
# USERS (luôn ghi đè về đúng snapshot này)
# ----------------------------------------------------------------------
DRIVER_ROLE = 'DP Driver'
SIM_ROLE = 'DP GPS Simulator'

# Page mà tài xế và simulator được mở
DRIVER_PAGES = ('driver-gps', 'driver_gps')

USERS = [
    dict(email='gps.simulator@dongphong.local', first_name='GPS', last_name='Simulator',
         password='Simulator@1234', role=SIM_ROLE, mobile=None,
         # API key/secret cố định để simulator.py không phải đổi cấu hình sau mỗi lần reset
         api_key='dpsimulatorkey0001', api_secret='dpsimulatorsecret0001',
         driver_name=None, vehicle=None),
    dict(email='binh.driver@dongphong.local', first_name='Bình', last_name='Trần Minh',
         password='Driver@1234', role=DRIVER_ROLE, mobile='0902345678',
         api_key=None, api_secret=None,
         driver_name='Trần Minh Bình', vehicle='51C-234.56'),
]

# Quyền doctype cho từng role: {role: {doctype: (read, write, create)}}
ROLE_PERMISSIONS = {
    SIM_ROLE: {
        'Vehicle': (1, 1, 1),
        'Delivery Trip': (1, 1, 1),
        'GPS Log': (1, 1, 1),
    },
    DRIVER_ROLE: {
        'Vehicle': (1, 1, 1),
        'Driver': (1, 1, 1),
        'Delivery Trip': (1, 1, 1),
        'GPS Log': (1, 1, 1),
    },
}


def _haversine(a, b):
    r = 6371.0088
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _link_or_fallback(doctype, wanted):
    if frappe.db.exists(doctype, wanted):
        return wanted
    filters = {}
    if frappe.get_meta(doctype).has_field('is_group'):
        filters['is_group'] = 0
    found = frappe.get_all(doctype, filters=filters, pluck='name', limit=1)
    if not found:
        raise RuntimeError('Không tìm thấy %s nào (cần có "%s").' % (doctype, wanted))
    return found[0]


def _only_existing_fields(doctype, values):
    meta = frappe.get_meta(doctype)
    return {k: v for k, v in values.items() if k == 'doctype' or meta.has_field(k)}


def _plan_route(stop_idx, departure):
    pts = [(DEPOT['lat'], DEPOT['lng'])] + [(STOPS[i]['lat'], STOPS[i]['lng']) for i in stop_idx]
    t = get_datetime(departure)
    legs, total = [], 0.0
    for a, b in zip(pts, pts[1:]):
        km = round(_haversine(a, b) * ROAD_FACTOR, 1)
        t = add_to_date(t, minutes=int(round(km / AVG_SPEED_KMH * 60)))
        legs.append(dict(km=km, arrival=t))
        total += km
        t = add_to_date(t, minutes=STOP_SERVICE_MIN)
    back = round(_haversine(pts[-1], pts[0]) * ROAD_FACTOR, 1)
    total += back
    end = add_to_date(t, minutes=int(round(back / AVG_SPEED_KMH * 60)))
    return dict(legs=legs, total_km=round(total, 1), end=end)


# ----------------------------------------------------------------------
# [1/5] Dọn dữ liệu cũ
# ----------------------------------------------------------------------
def clear_old_data():
    """Xóa các dữ liệu giao dịch GPS & Delivery Trip thử nghiệm cũ và reset bộ đếm ID."""
    print(">>> [1/5] Đang dọn dẹp dữ liệu cũ (GPS Log, Delivery Trip, Naming Series)...")
    frappe.db.sql("DELETE FROM `tabGPS Log` ")
    frappe.db.sql("DELETE FROM `tabDelivery Stop` ")
    frappe.db.sql("DELETE FROM `tabDelivery Trip` ")

    # RESET BỘ ĐẾM ID (NAMING SERIES) theo định dạng 'MAT-DT-YYYY-'
    current_year = today().split('-')[0]
    prefix = f"MAT-DT-{current_year}-"
    frappe.db.sql("DELETE FROM `tabSeries` WHERE name = %s", prefix)

    frappe.db.commit()


# ----------------------------------------------------------------------
# [2/5] Master data
# ----------------------------------------------------------------------
def seed_master_data():
    """Tạo lại Xe, Tài xế, Khách hàng & Địa chỉ mẫu."""
    print(">>> [2/5] Đang tạo lại Master Data (Vehicles, Drivers, Customers, Addresses)...")

    # 1. Vehicles
    for plate, make, model, payload, fuel, km, status in VEHICLES:
        if not frappe.db.exists('Vehicle', plate):
            doc = frappe.get_doc(dict(
                doctype='Vehicle', license_plate=plate, make=make, model=model,
                last_odometer=km, fuel_type=fuel, uom='Litre', location=DEPOT['name'],
                custom_payload_capacity_kg=payload, custom_technical_status=status))
            doc.insert(ignore_permissions=True)

    # 2. Drivers
    driver_names = []
    for full_name, phone, lic_no in DRIVERS:
        existing = frappe.get_all('Driver', filters={'full_name': full_name}, pluck='name')
        if existing:
            driver_names.append(existing[0])
        else:
            values = dict(doctype='Driver', full_name=full_name, status='Active', naming_series='HR-DRI-.YYYY.-',
                          cell_number=phone, license_number=lic_no,
                          issuing_date=add_days(today(), -1500), expiry_date=add_days(today(), 1500))
            doc = frappe.get_doc(_only_existing_fields('Driver', values))
            doc.insert(ignore_permissions=True)
            driver_names.append(doc.name)

    # 3. Customers & Addresses
    group = _link_or_fallback('Customer Group', DEFAULT_CUSTOMER_GROUP)
    territory = _link_or_fallback('Territory', DEFAULT_TERRITORY)
    stops = []
    for s in STOPS:
        customer = frappe.db.get_value('Customer', {'customer_name': s['title']}, 'name')
        if not customer:
            doc = frappe.get_doc(dict(doctype='Customer', customer_name=s['title'], customer_type='Company',
                                      customer_group=group, territory=territory))
            doc.insert(ignore_permissions=True)
            customer = doc.name

        addr_title = s['title'].replace('Điểm giao', 'Địa chỉ giao')
        address = frappe.db.get_value('Address', {'address_title': addr_title}, 'name')
        addr_values = dict(address_line1=s['line1'], county=s['county'], city=s['city'], state=s['state'],
                           pincode=s['pincode'], country='Vietnam', is_shipping_address=1)
        if not address:
            doc = frappe.get_doc(dict(doctype='Address', address_title=addr_title, address_type='Shipping',
                                      links=[dict(link_doctype='Customer', link_name=customer)], **addr_values))
            doc.insert(ignore_permissions=True)
            address = doc.name
        else:
            frappe.db.set_value('Address', address, addr_values, update_modified=False)

        frappe.db.set_value('Address', address, {
            'custom_latitude': s['lat'], 'custom_longitude': s['lng'], 'custom_geocode_source': 'Manual'},
            update_modified=False)
        stops.append((customer, address))

    frappe.db.commit()
    return driver_names, stops


# ----------------------------------------------------------------------
# [3/5] Users & Access Rights
# ----------------------------------------------------------------------
def _ensure_roles():
    for role in (DRIVER_ROLE, SIM_ROLE):
        if not frappe.db.exists('Role', role):
            frappe.get_doc(dict(doctype='Role', role_name=role, desk_access=1)).insert(ignore_permissions=True)


def _reset_role_permissions():
    """Xóa quyền cũ của các role DP rồi tạo lại theo ROLE_PERMISSIONS."""
    from frappe.permissions import add_permission, update_permission_property

    for role, perms in ROLE_PERMISSIONS.items():
        frappe.db.delete('Custom DocPerm', {'role': role})
        for doctype, (read, write, create) in perms.items():
            if not frappe.db.exists('DocType', doctype) or frappe.get_meta(doctype).istable:
                continue
            add_permission(doctype, role, 0)
            update_permission_property(doctype, role, 0, 'read', read)
            update_permission_property(doctype, role, 0, 'write', write)
            update_permission_property(doctype, role, 0, 'create', create)
    frappe.db.commit()


def _ensure_driver_user_field():
    """Đảm bảo Driver có trường custom_user (Link -> User)."""
    meta = frappe.get_meta('Driver')
    if meta.has_field('custom_user') or meta.has_field('user'):
        return
    from frappe.custom.doctype.custom_field.custom_field import create_custom_field
    create_custom_field('Driver', dict(
        fieldname='custom_user', label='User', fieldtype='Link', options='User',
        insert_after='employee', unique=0))
    frappe.clear_cache(doctype='Driver')
    print('    + Đã tạo Custom Field Driver.custom_user')


def _upsert_user(u):
    """Tạo mới hoặc ghi đè user: thông tin, role duy nhất, enabled, API key, mật khẩu."""
    email = u['email']
    if frappe.db.exists('User', email):
        user = frappe.get_doc('User', email)
        action = 'Ghi đè'
    else:
        user = frappe.new_doc('User')
        user.email = email
        action = 'Tạo mới'

    user.first_name = u['first_name']
    user.last_name = u['last_name']
    user.mobile_no = u.get('mobile')
    user.enabled = 1
    user.user_type = 'System User'
    user.send_welcome_email = 0

    # Ghi đè role: chỉ giữ đúng role quy định của snapshot
    user.set('roles', [])
    user.append('roles', {'role': u['role']})

    if u.get('api_key'):
        user.api_key = u['api_key']
        user.api_secret = u['api_secret']

    user.flags.ignore_permissions = True
    user.save(ignore_permissions=True)

    # Ghi đè mật khẩu và đăng xuất các phiên cũ
    update_password(email, u['password'], logout_all_sessions=True)
    print('    + %s user %s (role: %s)' % (action, email, u['role']))


def _link_driver(email, driver_name):
    """Liên kết User -> Driver (mỗi email chỉ gắn với đúng 1 Driver)."""
    meta = frappe.get_meta('Driver')
    field = next((f for f in ('custom_user', 'user') if meta.has_field(f)), None)
    if not field:
        print('      ! Driver chưa có trường custom_user, chưa liên kết được.')
        return None

    drv = frappe.db.get_value('Driver', {'full_name': driver_name}, 'name')
    if not drv:
        print('      ! Không tìm thấy Driver "%s".' % driver_name)
        return None

    # Gỡ liên kết cũ của email này ở các Driver khác
    for other in frappe.get_all('Driver', filters={field: email, 'name': ['!=', drv]}, pluck='name'):
        frappe.db.set_value('Driver', other, field, None, update_modified=False)
    frappe.db.set_value('Driver', drv, field, email, update_modified=False)
    print('      Đã liên kết %s -> Driver %s (%s)' % (email, drv, field))
    return drv


def _grant_page_permissions():
    """Gán quyền truy cập Page driver-gps cho cả DRIVER_ROLE và SIM_ROLE."""
    target_roles = [DRIVER_ROLE, SIM_ROLE]
    for page_name in DRIVER_PAGES:
        if frappe.db.exists('Page', page_name):
            page = frappe.get_doc('Page', page_name)
            existing_roles = {r.role for r in page.roles}
            updated = False
            for role in target_roles:
                if role not in existing_roles:
                    page.append('roles', {'role': role})
                    updated = True
            if updated:
                page.save(ignore_permissions=True)
                print('      + Đã cấp quyền Page %s cho roles: %s' % (page_name, ', '.join(target_roles)))


def _reset_driver_access(email, driver, vehicle):
    """Tạo lại User Permission (Driver, Vehicle) cho tài xế."""
    frappe.db.delete('User Permission', {'user': email})
    targets = [('Driver', driver)]
    if vehicle:
        targets.append(('Vehicle', vehicle))
    for allow, value in targets:
        frappe.get_doc(dict(
            doctype='User Permission',
            user=email,
            allow=allow,
            for_value=value,
            apply_to_all_doctypes=1
        )).insert(ignore_permissions=True)
        print('      + User Permission: %s = %s' % (allow, value))


def seed_users():
    """Ghi đè 2 user: GPS Simulator và tài xế Trần Minh Bình."""
    print(">>> [3/5] Đang ghi đè User, Role Permissions & Page Access...")

    _ensure_roles()
    _reset_role_permissions()
    _ensure_driver_user_field()
    _grant_page_permissions()

    for u in USERS:
        _upsert_user(u)
        if u['driver_name']:
            drv = _link_driver(u['email'], u['driver_name'])
            if drv:
                _reset_driver_access(u['email'], drv, u.get('vehicle'))

    frappe.db.commit()

    sim = next(x for x in USERS if x['api_key'])
    print('    --- Thông tin đăng nhập snapshot ---')
    for u in USERS:
        print('    %s / %s' % (u['email'], u['password']))
    print('    Simulator header: Authorization: token %s:%s' % (sim['api_key'], sim['api_secret']))


# ----------------------------------------------------------------------
# [4/5] + [5/5] Chuyến hàng & GPS snapshot
# ----------------------------------------------------------------------
def seed_trips_and_gps(drivers, stops):
    """Tạo mới các chuyến hàng active mẫu và thiết lập GPS snapshot ban đầu."""
    print(">>> [4/5] Đang tạo Chuyến hàng mẫu (Delivery Trip) & Tọa độ xuất phát...")
    odo = {v[0]: v[5] for v in VEHICLES}
    uom = frappe.db.exists('UOM', 'Km') or 'Km'

    for offset, plate, d_idx, hour, stop_idx, load, done in sorted(TRIPS, key=lambda t: t[0]):
        departure = '%s %02d:00:00' % (add_days(today(), offset), hour)
        plan = _plan_route(stop_idx, departure)
        start_km = odo[plate]
        end_km = start_km + int(round(plan['total_km'])) if done else 0
        if done:
            odo[plate] = end_km

        values = dict(
            doctype='Delivery Trip', company=COMPANY, vehicle=plate,
            driver=drivers[d_idx], driver_name=DRIVERS[d_idx][0], departure_time=departure,
            naming_series='MAT-DT-.YYYY.-', status='Draft',
            delivery_stops=[dict(customer=stops[i][0], address=stops[i][1]) for i in stop_idx])

        doc = frappe.get_doc(_only_existing_fields('Delivery Trip', values))
        doc.insert(ignore_permissions=True)
        trip = doc.name

        # Ghi tọa độ & khoảng cách
        frappe.db.set_value('Delivery Trip', trip, _only_existing_fields('Delivery Trip', {
            'custom_origin_lat': DEPOT['lat'], 'custom_origin_lng': DEPOT['lng'],
            'custom_planned_load_kg': load, 'custom_start_odometer': start_km, 'custom_end_odometer': end_km,
            'custom_expected_end_time': plan['end'].strftime('%Y-%m-%d %H:%M:%S'),
            'total_distance': plan['total_km'], 'uom': uom
        }), update_modified=False)

        rows = frappe.get_all('Delivery Stop', filters={'parent': trip, 'parenttype': 'Delivery Trip'},
                              fields=['name'], order_by='idx asc')
        for row, i, leg in zip(rows, stop_idx, plan['legs']):
            frappe.db.set_value('Delivery Stop', row.name, _only_existing_fields('Delivery Stop', {
                'lat': STOPS[i]['lat'], 'lng': STOPS[i]['lng'], 'distance': leg['km'],
                'estimated_arrival': leg['arrival'], 'uom': uom
            }), update_modified=False)

    print(">>> [5/5] Cập nhật Snapshot vị trí GPS ban đầu cho các xe...")
    now = now_datetime()
    age = {'Available': dict(minutes=-2), 'Under Maintenance': dict(days=-3), 'Out of Service': dict(days=-10)}
    for i, (plate, _make, _model, _payload, _fuel, _km, status) in enumerate(VEHICLES):
        frappe.db.set_value('Vehicle', plate, {
            'custom_gps_device_id': 'DP-GPS-%03d' % (i + 1),
            'custom_last_lat': round(DEPOT['lat'] + i * 0.0007, 9),
            'custom_last_lng': round(DEPOT['lng'] + i * 0.0009, 9),
            'custom_last_gps_time': add_to_date(now, **age[status]),
            'location': DEPOT['name'],
        }, update_modified=False)


def reset_all_data():
    print("==================================================")
    print("🔄 BẮT ĐẦU RESET & SEED LẠI DỮ LIỆU DEMO ĐÔNG PHONG")
    print("==================================================")

    clear_old_data()
    drivers, stops = seed_master_data()
    seed_users()
    seed_trips_and_gps(drivers, stops)

    frappe.clear_cache()
    frappe.db.commit()

    print("==================================================")
    print("🎉 TÁI TẠO DỮ LIỆU DEMO THÀNH CÔNG!")
    print("==================================================")


if __name__ == "__main__":
    reset_all_data()