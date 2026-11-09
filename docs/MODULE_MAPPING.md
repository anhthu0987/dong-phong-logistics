# Module nghiệp vụ và ánh xạ ERPNext

App cài đặt vẫn là `dp_dispatch`. Các module tự xây được tách theo trách nhiệm;
DocType chuẩn giữ nguyên module của ERPNext/HRMS.

| Khối nghiệp vụ | Module kỹ thuật | Dữ liệu & Tính năng |
|---|---|---|
| Khách hàng và báo giá | Selling/CRM chuẩn; Workspace DP Sales | Customer, Quotation, Sales Order, Item, Item Price |
| Đơn vận chuyển | DP Transport Orders | Delivery Order, Delivery Order Item |
| Xe, tài xế và vận hành | DP Fleet Operations + Fleet chuẩn | Fleet Maintenance Plan/Record; liên kết Vehicle, Driver, Employee, Vehicle Log (chi phí chuyến) |
| Điều phối và quản lý chuyến | DP Transport Planning + Stock chuẩn | Mở rộng Delivery Trip/Delivery Stop; Transport Plan (tối ưu lộ trình VRP qua OSRM & Google OR-Tools) |
| Theo dõi và giao nhận | DP Tracking and POD | Delivery Confirmation/Item (ePOD); GPS Log, Fleet Map realtime qua Socket.IO |
| Hóa đơn, công nợ và báo cáo | Accounts chuẩn; Workspace DP Accounts | Sales Invoice, Payment Entry, Journal Entry, Báo cáo đối soát vận tải Transport Reconciliation |

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

## Các phân hệ nâng cao đã tích hợp hoàn chỉnh

1. **GPS Realtime & Bản đồ theo chuyến**: Đã kết nối Socket.IO, cập nhật tọa độ tức thời và lịch sử di chuyển theo chuyến, xem [GPS_INTEGRATION](GPS_INTEGRATION.md).
2. **Kế hoạch tuyến đường thông minh (OSRM + OR-Tools)**: Đã tích hợp DocType `Transport Plan`, dịch vụ FastAPI `optimizer` và engine OSRM (OpenStreetMap) nội bộ để giải bài toán VRP đa xe, ràng buộc tải trọng, thời gian và tọa độ, xem [PLANNING_OSRM](PLANNING_OSRM.md).
3. **Tích hợp Kế toán vận tải tự động**: Đã kết nối vòng đời hoàn tất chuyến với `Sales Invoice`, thu cước `Payment Entry`, chi phí `Journal Entry` và báo cáo đối soát `Transport Reconciliation`, xem [ACCOUNTING_INTEGRATION](ACCOUNTING_INTEGRATION.md).

## Ranh giới mã nguồn hiện tại

- Các package nghiệp vụ sở hữu metadata/controller DocType; logic dùng chung vẫn
  ở gốc `dp_dispatch`: `transport.py`, `validation.py`, `completion.py`,
  `delivery_confirmation.py`, `maintenance.py` và `permissions.py`.
- `hooks.py` nối document events và quyền vào các hàm này. Giữ đường dẫn hiện tại
  để API và Client Script đang dùng không bị gãy.
- GPS Log thuộc DP Tracking and POD, nhưng hai Page GPS vẫn thuộc DP Dispatch.
  Nguồn JavaScript duy nhất là `dp_dispatch/dp_dispatch/page/<page>/<page>.js`
  tính từ thư mục app. Frappe đọc trực tiếp theo module của Page; không đăng ký
  thêm `page_js` cho hai trang này. Mỗi trang phải có JSON metadata đi kèm để
  migration không coi là Page mồ côi và thay mã JS bằng trang mẫu. API GPS giữ
  đường dẫn tương thích cũ.
- Đây là một app triển khai chung, không phải sáu app hay sáu dịch vụ độc lập.

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


### Nhánh realtime GPS (bước 4)

`DP Tracking and POD` sở hữu `dp_tracking_and_pod/realtime.py`: quyền theo dõi,
lease ngắn hạn và sự kiện vị trí. API nhận GPS/Redis và Page vẫn giữ đường dẫn cũ
để tương thích; không đổi module DocType chuẩn. Service `websocket` là lớp hạ tầng
Socket.IO dùng chung, còn quyền và ý nghĩa sự kiện GPS thuộc Tracking/POD.
Xem [GPS_INTEGRATION](GPS_INTEGRATION.md) để phân biệt phần đã làm với TCP Listener,
AI/OR-Tools và phát hiện lệch tuyến ở bước sau.
