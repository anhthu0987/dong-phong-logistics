# Module nghiệp vụ và ánh xạ ERPNext

App cài đặt vẫn là `dp_dispatch`. Các module tự xây được tách theo trách nhiệm;
DocType chuẩn giữ nguyên module của ERPNext/HRMS.

| Khối nghiệp vụ | Module kỹ thuật | Dữ liệu |
|---|---|---|
| Khách hàng và báo giá | Selling/CRM chuẩn; Workspace DP Sales | Customer, Quotation, Sales Order, Item, Item Price |
| Đơn vận chuyển | DP Transport Orders | Delivery Order, Delivery Order Item |
| Xe, tài xế và vận hành | DP Fleet Operations + Fleet chuẩn | Fleet Maintenance Plan/Record; liên kết Vehicle, Driver, Employee, Vehicle Log |
| Điều phối và quản lý chuyến | DP Transport Planning + Stock chuẩn | Mở rộng Delivery Trip/Delivery Stop; chưa có chứng từ kế hoạch tối ưu |
| Theo dõi và giao nhận | DP Tracking and POD | Delivery Confirmation/Item; GPS Log/Device chỉ xuất hiện khi đã được cài |
| Hóa đơn, công nợ và báo cáo | Accounts chuẩn; Workspace DP Accounts | Sales Invoice, Purchase Invoice, Payment Entry |

`DP Dispatch` được giữ làm module đầu mối và Workspace tổng quan để các liên kết
cũ vẫn mở được. Nó không còn sở hữu sáu DocType nghiệp vụ tự xây.
Hai Workspace DP Sales/DP Accounts không phải hai module kế toán/bán hàng mới.

## Cài mới và nâng cấp

- JSON và controller của DocType tự xây nằm trong package tương ứng với module mới.
- `bench --site <site> migrate` đồng bộ Module Def và cập nhật trường module trên
  DocType hiện có. Tên DocType, bảng dữ liệu, tên bản ghi và Link không đổi.
- Hook after_install/after_migrate tạo lại sáu Workspace và trang tổng quan.
  Sidebar chỉ cài khi phiên bản Frappe có DocType Sidebar.
- Giữ nguyên đường dẫn API/hook nghiệp vụ ở gốc package `dp_dispatch`.
- Sao lưu site trước nâng cấp; build image và cập nhật toàn bộ backend/worker
  cùng phiên bản trước khi kiểm tra. Không chỉ chép code vào một container.
- Không cài thêm hoặc gỡ `dp_operations` trong thay đổi này.

Việc tách module không tự bổ sung GPS, OR-Tools, Sales Order mapping hay tích hợp
kế toán. Các liên kết tới DocType chuẩn là điểm truy cập; luồng tích hợp vẫn cần
được triển khai và nghiệm thu riêng.

## Kiểm chứng local

Đã build và migrate thành công trên site `logistics.localhost` (Frappe v15,
cổng 8085), có backup database và file trước nâng cấp. Kiểm tra sáu controller,
module sở hữu, bảy Workspace (sáu nghiệp vụ + tổng quan), chạy lại cài Workspace
không tạo trùng và DocType chuẩn không bị chuyển module đều đạt.
Sáu bảng tùy chỉnh đang rỗng trước/sau migration, nên chưa chứng minh nâng cấp
với dữ liệu giao dịch thực tế hoặc toàn bộ luồng nghiệp vụ trên site này.

Chạy kiểm tra từ PowerShell tại thư mục repo:

```powershell
Get-Content erpnext-local/dispatch-app/verify_modules.py -Raw | docker exec -i -w /home/frappe/frappe-bench/sites logistics-erpnext-backend-1 /home/frappe/frappe-bench/env/bin/python -
```
