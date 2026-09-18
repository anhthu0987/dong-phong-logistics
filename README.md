# Đông Phong Logistics

Dự án nhóm 3 người: cấu hình và mở rộng ERPNext/Frappe HR để mô phỏng điều phối vận tải liên vùng. Repository lưu code tùy chỉnh và hướng dẫn; dữ liệu ERPNext nằm trên máy chủ, không nằm trong GitHub.

## Phân công

| Thành viên | Phạm vi | Nhánh đề xuất |
|---|---|---|
| 1 | Xe, tài xế, điều phối, tích hợp bản chung | feature/dispatch |
| 2 | Giao nhận, nhiên liệu, bảo trì | feature/operations |
| 3 | GPS giả lập, API và bản đồ | feature/gps |

Chi tiết: [Hướng dẫn thành viên 2 và 3](docs/PHAN_CONG.md).

## Code hiện có

- [Ứng dụng dp_dispatch](erpnext-local/dispatch-app): kiểm tra lịch, tải trọng, thời gian, số km và tình trạng xe/tài xế.
- [Thiết lập dữ liệu](erpnext-local/database): Custom Fields và dữ liệu mô phỏng xe/tài xế/chuyến. Không tạo GPS hoặc nghiệp vụ của hai thành viên còn lại.
- [Kết quả 20 ca kiểm tra](erpnext-local/dispatch-app/test-results.json): chạy trên site cục bộ; không phải CI.
- Chuyến mẫu còn Draft; chưa hoàn thành giao nhận xuyên suốt. Chưa mở LAN và chưa tạo tài khoản nhóm.

## Làm việc nhóm

1. Clone repository. Mỗi người checkout nhánh của mình từ main.
2. Thay đổi code trong phạm vi được phân công, commit và push nhánh.
3. Tạo Pull Request vào main; một thành viên khác xem và kiểm tra trước khi ghép.
4. Thành viên 1 triển khai thay đổi lên ERPNext chung. Push GitHub không tự triển khai và không đồng bộ database.
5. Không commit mật khẩu, token, .env, backup hoặc dữ liệu thật. Mỗi người tự tạo .env từ .env.example.

Chưa mời thành viên: cần username GitHub của hai bạn. Nhánh đề xuất không thay thế việc kiểm tra quyền truy cập repository.

## Chạy trên máy đã có ERPNext của nhóm

Code runtime hiện ở thư mục erpnext-local gốc trên máy chủ; bản trong repository là bản chụp ban đầu. Sau khi ghép code, đối chiếu/copy các tệp đã review về thư mục runtime trước khi chạy Deploy.ps1 tại đó. Không chạy hai hệ thống cùng project name và cổng một lúc.

Xem [hướng dẫn triển khai app](erpnext-local/dispatch-app/README.md). Không chạy install lại site đang có; sao lưu trước khi migrate.

## Chuẩn bị máy mới

Máy cần Git và Docker Desktop với Linux containers. Repo không chứa toàn bộ ERPNext hoặc image nền. Làm trong thư mục erpnext-local của bản clone:

1. Clone `https://github.com/frappe/frappe_docker.git` vào `frappe_docker`; bản nguồn tham chiếu: `a0c52135d4d41c4b8acf7adfdfc5bbcba46dd4d0`.
2. Tạo .env từ .env.example và đặt mật khẩu riêng.
3. Chạy `./Quan-ly.ps1 build` để build image nền. apps.json theo nhánh version-15, nên lần build mới có thể khác patch version máy chủ; cần kiểm tra tương thích.
4. Build image bổ sung: `docker build -t logistics-erpnext:dispatch-v1 ./dispatch-app`.
5. Chạy `./Quan-ly.ps1 start`, rồi `./Quan-ly.ps1 install` **chỉ khi site chưa tồn tại**.
6. Hoàn tất setup wizard với công ty mô phỏng Đông Phong. Tạo xe mẫu 51C-123.45 trước khi chạy database/Install-Database.ps1; trình cài dữ liệu hiện dùng xe này và cần UOM Litre, nhóm khách Commercial, lãnh thổ Vietnam có sẵn.
7. Chạy database/Install-Database.ps1, sau đó dispatch-app/Deploy.ps1.

Môi trường tham chiếu đã kiểm tra: ERPNext 15.121.2, Frappe 15.120.1, HRMS 15.64.0. Quy trình bootstrap máy mới chưa được kiểm thử từ đầu trong repo này; có thể dùng máy chủ hiện tại để cùng thao tác trong thời gian chuẩn bị môi trường riêng.
