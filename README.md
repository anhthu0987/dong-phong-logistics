# Đông Phong Logistics

Repository cho ứng dụng Frappe `dp_dispatch` và môi trường ERPNext local phục vụ mô phỏng điều phối giao hàng.

## Bắt đầu tại đây

- [COMMAND_README](docs/COMMAND_README.md): tổng hợp file YAML/JSON cấu hình Docker, lệnh PowerShell, init site, build, chạy, backup và deploy. Dùng tài liệu này khi cài hoặc vận hành môi trường.
- [DOC_README](docs/DOC_README.md): kiến trúc app, cấu trúc thư mục, DocType/schema, luồng nghiệp vụ, validation và API.
- [Phân công nhóm](docs/PHAN_CONG.md): phạm vi ban đầu của các thành viên. Một số nội dung trong tài liệu phân công là kế hoạch ban đầu; xem DOC_README để biết trạng thái code hiện tại.
- [Thành viên 2 – hướng dẫn vận hành](docs/THANH_VIEN_2.md).
- [Thay đổi luồng sau demo](docs/THAY_DOI_VAN_HANH_SAU_DEMO.md).

## Các thành phần

- `erpnext-local/dispatch-app`: ứng dụng Frappe, validation điều phối và các phần nghiệp vụ tích hợp.
- `erpnext-local/frappe_docker`: mã triển khai tham chiếu, được clone cục bộ theo commit ghi trong hướng dẫn cài đặt; không được commit vào Git.
- `erpnext-local/database`: script dữ liệu mẫu cũ dành cho site v15. Không chạy script này trên site v16.

## Cẩn trọng với cấu hình riêng

Không commit `.env`, mật khẩu, token, bản backup, dữ liệu thật hoặc thư mục `frappe_docker`. Chỉ dùng thông tin giả lập cho demo. Site v15 ở cổng 8085 và site v16 ở cổng 8086 có project/database riêng; không trỏ một stack sang database của stack còn lại.
