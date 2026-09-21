# GPS — giao diện gốc và các sửa lỗi tối thiểu

Bản này giữ Fleet Map, trang tài xế và tuyến giả lập của feature/gps. Các thay đổi: khai báo module/package; thống nhất đường dẫn API; giới hạn GPS tài xế theo chuyến; chặn xác nhận chuyến đã hủy; gửi GPS bằng API token.

## Chạy simulator

1. Tạo tài khoản hệ thống dành cho simulator, cấp role `DP GPS Simulator`. Quản trị viên tạo API Key/Secret trong User. API hiện cho role simulator gửi GPS theo phạm vi logic của code; chưa bổ sung giới hạn thiết bị theo từng xe.
2. Sao chép `dp_dispatch/dp_dispatch/gps_config.example.json` thành `gps_config.local.json` cùng thư mục. Điền khóa, xe, chuyến và địa chỉ server. `site` phải khớp site Frappe; có thể bỏ trường này khi hostname truy cập đã định tuyến đúng site. `time_zone` khớp múi giờ của site.
3. Cấu hình riêng bị Git và Docker build bỏ qua. Có thể dùng biến môi trường `DP_GPS_API_KEY`, `DP_GPS_API_SECRET` thay cho hai trường trong file.

Chạy Python trên máy có `requests` và dữ liệu múi giờ (Windows có thể cần `tzdata`):

```powershell
python -m pip install requests tzdata
python dp_dispatch/dp_dispatch/simulator.py --config dp_dispatch/dp_dispatch/gps_config.local.json
```

Trên container phát triển hiện tại, source được bind mount và đã có dependencies:

```powershell
docker exec -e DP_GPS_BASE_URL=http://127.0.0.1:8000 dp-gps-original /home/frappe/frappe-bench/env/bin/python /home/frappe/frappe-bench/apps/dp_dispatch/dp_dispatch/dp_dispatch/simulator.py
```

Mỗi lần chạy có ID riêng; tuyến 20 điểm giữ nguyên. Khi bị từ chối, chương trình dừng và trả mã lỗi khác 0. Không tự thử lại bản tin lỗi.

## Sau khi sửa code

```powershell
docker exec dp-gps-original bench --site gps-review.localhost clear-cache
docker restart dp-gps-original
```

Tải lại trang với Ctrl+Shift+R. Tên container/site ở trên thuộc máy demo, cần đổi nếu cài ở máy khác. Cổng truy cập máy chủ là 8086; cổng bên trong container là 8000.

## Cài schema ở môi trường mới

Repo này là monorepo; app ở `erpnext-local/dispatch-app`, không phải thư mục gốc repository. Cài Frappe/ERPNext/HRMS v15 và app `dp_dispatch`, sau đó chạy riêng `database/install.py` trong context của site để tạo GPS Log và trường GPS. Không chạy script reset/seed cũ: `reset_seed.py` đã được vô hiệu hóa để giữ dữ liệu và không phát tán thông tin xác thực hardcode. Các lệnh cài database đời cũ có gọi seeder cần được tách bước, không dùng nguyên chuỗi đó.

## Kiểm tra

- `tests/test_simulator_auth.py`: 4 ca xác thực, ưu tiên biến môi trường, ID lượt chạy, dừng khi 403.
- `tests/gps_permissions_integration.py`: 20 ca trên site thử gps-review.localhost; rollback dữ liệu; không chạy trên production.
- Đã gửi trực tiếp 20/20 điểm thành công bằng token qua HTTP ở môi trường thử.

## Giới hạn còn lại

Chưa sửa script bản đồ trong phiếu chuyến còn tham chiếu GPS Location Log/đường dẫn asset; chưa sửa kiểm tra xung đột source_event_id khác thời gian; quyền All/read trong script cài schema gốc vẫn cần rà soát nếu cài mới. Sửa quyền trong bản này áp dụng các API GPS tùy chỉnh, chưa phải rà soát toàn bộ API REST và quyền DocType. Giao diện và luồng chính được giữ nguyên theo yêu cầu.
