# Database – nhiệm vụ thành viên 1

> Tài liệu này mô tả bộ cài schema và dữ liệu demo cũ dành cho site v15. Code vận hành hiện tại đã mở rộng; xem [DOC_README](../../docs/DOC_README.md) để đọc schema/feature/API đang tích hợp và [COMMAND_README](../../docs/COMMAND_README.md) để chọn đúng lệnh theo phiên bản. Không chạy bộ cài v15 trên site v16.

Doanh nghiệp: Công ty Phân phối Đông Phong (DP).

## Đã triển khai

- Dùng lại Vehicle, Driver, Delivery Trip, Delivery Stop cùng Company, Customer, Address và Dynamic Link có sẵn.
- Vehicle: thêm `custom_payload_capacity_kg` (kg), `custom_technical_status` (Available / Under Maintenance / Out of Service).
- Delivery Trip: thêm `custom_expected_end_time`, `custom_start_odometer`, `custom_end_odometer`.
- Bật Allow Import cho Vehicle; cấp Import cho vai trò Fleet Manager. Không thêm vai trò vào tài khoản của người dùng.
- Tạo đủ 3 xe, 3 tài xế giả lập và 1 chuyến nháp có điểm giao mẫu. Xe 51C-123.45 đã có được giữ nguyên.
- Tải trọng chưa có thông số xác minh nên để trống. Các biển số, người và điểm giao đều là dữ liệu mô phỏng.

## Mở để kiểm tra

- Xe: http://localhost:8085/app/vehicle
- Tài xế: http://localhost:8085/app/driver
- Chuyến nháp: http://localhost:8085/app/delivery-trip/MAT-DT-2026-00001

Chuyến mẫu chưa có Delivery Note, chưa Submit và chưa phải chuyến giao hàng hoàn chỉnh.

## Cài lại và chia sẻ cho nhóm

Sao lưu site trước, rồi chạy `Install-Database.ps1` bằng PowerShell trên môi trường ERPNext/HRMS hiện tại. Script dùng container `logistics-erpnext-backend-1` và site `logistics.localhost`. Nếu máy khác có tên khác, sửa wrapper và run_install.sh cho đúng.

Script dùng API metadata/Document của Frappe, không sửa mã nguồn ERPNext. Chạy lại sẽ giữ dữ liệu mẫu đã tồn tại, không tạo lặp. Custom Fields và Property Setter lưu trong database, tồn tại qua khởi động lại container.

- `install_schema.py`: cấu hình có thể lưu Git và chạy lại.
- `metadata.json`: danh mục trường và kiểu cột thực tế của 8 bảng trong phạm vi này.
- `schema-reference.sql`: DDL trích từ database để tham khảo, KHÔNG dùng để dựng lại ERPNext bằng cách chạy SQL trực tiếp.
- `installation-result.json`: kết quả lần chạy gần nhất.

## Cập nhật phần xử lý điều phối

Ứng dụng `dp_dispatch` đã triển khai kiểm tra giờ kết thúc, lịch xe/tài xế đã Submit, tình trạng xe/tài xế, tải trọng và số km. Có thêm `custom_planned_load_kg` trên Delivery Trip. Xem `../dispatch-app/README.md` để biết quy tắc, giới hạn và cách thử; phần dữ liệu mẫu trong tài liệu này không đồng nghĩa đã chạy nghiệp vụ giao hàng hoàn chỉnh.

## Giới hạn phần dữ liệu

Khối lượng chuyến được khai báo thủ công; chưa tự tính từ hàng trên Delivery Note. Chưa kiểm tra hạng bằng lái, điều phối xe thay thế, lịch bảo trì tương lai hoặc xử lý chuyến trễ tự động.

Không tạo GPS Log, bảng bảo trì, xác nhận giao nhận hoặc liên kết chi phí; các phần này thuộc thành viên 2 và 3. Chưa mở LAN/VPN và chưa tạo tài khoản cho hai thành viên vì chưa có thông tin tài khoản.

## Kết quả kiểm tra

Sau cài đặt: 3 Vehicle, 3 Driver, 1 Delivery Trip. Chạy lại không tạo thêm bản ghi mẫu. Chuyến mẫu ở trạng thái Draft, liên kết xe và tài xế hợp lệ.

Backup trước thay đổi nằm trong `../backups/`, tiền tố `20260918_223703`. Không đưa backup, .env hoặc TAI_KHOAN.txt lên Git vì có thông tin riêng.
