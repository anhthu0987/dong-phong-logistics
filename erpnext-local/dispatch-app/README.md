# Đông Phong – điều phối (thành viên 1)

Ứng dụng Frappe `dp_dispatch`, Python, dùng biểu mẫu Delivery Trip có sẵn. Không sửa mã nguồn ERPNext; không triển khai GPS, nhiên liệu hay xác nhận giao nhận của các thành viên khác.

## Mã nguồn

- `dp_dispatch/validation.py`: kiểm tra phía máy chủ, áp dụng cho UI và API thông thường.
- `dp_dispatch/hooks.py`: nối các hàm kiểm tra vào sự kiện lưu/xác nhận chuyến và sửa số km sau Submit.
- `dp_dispatch/setup.py`: tạo/cập nhật trường và index qua Frappe.
- `tests_dispatch.py`: 20 kiểm tra tích hợp; dữ liệu thử được rollback.
- `Dockerfile`: thêm app vào image ERPNext đã cài.
- `Deploy.ps1`: build, chạy các container, cài app, migrate và khởi động lại dịch vụ.

## Quy tắc

1. Expected End Time phải sau Departure Time. Trước Submit phải có giờ kết thúc và tài xế.
2. Xe phải Available; tài xế phải Active. Nếu có ngày hết hạn giấy phép, ngày đó phải không sớm hơn ngày kết thúc chuyến. Chưa kiểm tra hạng giấy phép so với loại xe.
3. Planned Load (kg) là khối lượng nhập thủ công cho mô phỏng; chưa tự cộng từ phiếu xuất hàng. Khi Submit, tải trọng xe và khối lượng hàng phải > 0; khối lượng không được vượt tải trọng.
4. Chuyến đã Submit có trạng thái Scheduled/In Transit giữ xe và tài xế trong khoảng [giờ xuất phát, giờ kết thúc dự kiến). Hai chuyến nối tiếp đúng mốc được phép. Chuyến nháp không giữ lịch; khi Submit kiểm tra lại.
5. Chuyến Cancelled/Completed giải phóng lịch. Dùng trạng thái chuẩn ERPNext; dấu Visited ở các điểm giao quyết định In Transit/Completed. Đây không phải bằng chứng xác nhận nhận hàng của thành viên 2.
6. Số km không âm. End Odometer = 0 nghĩa là chưa nhập, nếu có thì không thấp hơn Start Odometer; được kiểm tra cả khi sửa sau Submit. Chưa đồng bộ tự động đồng hồ xe với nhật ký nhiên liệu.

Khoá dòng Vehicle/Driver và truy vấn lịch bằng locking read để tuần tự hoá các lần Submit dùng chung nguồn lực. Chưa có bài kiểm thử tải đồng thời hoặc hiệu năng. Không phải lịch theo GPS/thời gian thực; chuyến trễ phải được xử lý điều phối, hệ thống chưa tự gia hạn khoảng giữ lịch. Khoảng bảo trì tương lai chưa tích hợp.

## Tự xem và thử

1. Mở Vehicle 51C-123.45, nhập Payload Capacity (kg) = 2000, Technical Status = Available và Save. **2000 kg là giả định phục vụ bài demo, không khẳng định thông số xe thật.**
2. Mở chuyến nháp MAT-DT-2026-00001. Tải lại trình duyệt để nhận trường mới.
3. Chọn thời gian demo mới, Expected End Time sau Departure Time; Planned Load (kg) = 1000. Save.
4. Thử Planned Load = 2500 rồi Save: phải báo DP_OVERLOAD. Đổi lại 1000.
5. Thử giờ kết thúc trước xuất phát: phải báo DP_TIME. Khôi phục thời gian hợp lệ.
6. Submit chuyến. Tạo chuyến thứ hai có cùng xe hoặc tài xế và khoảng giờ giao nhau: hệ thống chặn DP_CONFLICT.
7. Thử khoảng giờ nối tiếp hoặc đổi cả xe và tài xế: được phép nếu các điều kiện khác hợp lệ.

Chuyến gốc được giữ ở Draft; thao tác Submit/Cancel trong hướng dẫn do người dùng thực hành. Dữ liệu hiện có vẫn gồm 3 xe, 3 tài xế và 1 chuyến mẫu.

## Cài lại

Cần image nền logistics-erpnext:v15, site logistics.localhost và cấu hình ../local.yaml dùng image dispatch-v1. Chạy ../database/Install-Database.ps1 để khởi tạo dữ liệu mẫu theo hướng dẫn tương ứng; chạy Deploy.ps1 để triển khai code. Sao lưu trước khi triển khai. Giữ image dispatch-v1 trong các lần start để app có mặt trong mọi Python worker.

Không đưa .env, TAI_KHOAN.txt hoặc backups lên Git. Có thể đưa toàn bộ thư mục dispatch-app vào repository của nhóm. Chưa tạo repo GitHub từ xa, tài khoản thành viên hay mở LAN/VPN.
