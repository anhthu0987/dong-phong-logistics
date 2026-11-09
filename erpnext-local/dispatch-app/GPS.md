# GPS tích hợp với vận tải v16

Luồng GPS và giao nhận đã nối theo `Delivery Trip`. Xem [hướng dẫn tích hợp và kiểm thử](../../docs/GPS_INTEGRATION.md).

## Simulator

1. Tài khoản simulator dùng role `DP GPS Simulator`, API key/secret do quản trị viên cấp.
2. Sao chép `dp_dispatch/dp_dispatch/gps_config.example.json` thành `gps_config.local.json`; điền server, xe và chuyến đã Submit, **đã bắt đầu** (In Transit).
3. Có thể dùng `DP_GPS_API_KEY` và `DP_GPS_API_SECRET`. Không commit thông tin xác thực.
4. Chạy `python dp_dispatch/dp_dispatch/simulator.py --config dp_dispatch/dp_dispatch/gps_config.local.json`.

Simulator gửi tọa độ mô phỏng; không chứng minh kết nối thiết bị GPS thật. GPS không tự hoàn tất điểm dừng hay chuyến.

## Triển khai v16

Build `Dockerfile.v16`, chạy `Quan-ly-v16.ps1 start` và `bench --site logistics-v16.localhost migrate`. Service `gps-flusher` ghi dữ liệu Redis vào MariaDB mỗi 3 giây. Schema và quyền GPS được cài qua `dp_dispatch.setup.install`; không chạy các script reset/seed cũ.

## Kiểm thử

- `tests/test_simulator_auth.py`: xác thực/config của simulator.
- `tests/gps_transport_integration.py`: quyền, đúng chuyến, Redis/MariaDB và luồng giao nhận hoàn chỉnh; rollback dữ liệu.
- `tests/gps_permissions_integration.py`: entry point tương thích, chuyển sang bài kiểm thử mới trên v16.
