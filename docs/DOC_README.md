# DOC_README — kiến trúc, schema và nghiệp vụ

## 1. Phạm vi

`dp_dispatch` là custom app Frappe bổ sung cho ERPNext/HRMS. Ứng dụng tái sử dụng DocType chuẩn (Vehicle, Driver, Employee, Delivery Trip, Delivery Stop, Quotation, Item, Item Price, Vehicle Log) và thêm metadata/chứng từ cho vận hành giao hàng. Không sửa trực tiếp mã nguồn `frappe`, `erpnext` hoặc `hrms`.

Trạng thái mô tả ở đây là code hiện có trong repository; cấu hình và dữ liệu trên từng site có thể khác. Site v16 local dùng `logistics-v16.localhost`; script dữ liệu mẫu v15 không tự chạy trên site này.

## 2. Cấu trúc thư mục

Module đã tách theo [bảng mapping](MODULE_MAPPING.md). Sáu DocType tự xây nằm
trong `dp_transport_orders/doctype`, `dp_fleet_operations/doctype` và
`dp_tracking_and_pod/doctype`. `dp_transport_planning` là module điều phối mở rộng
Delivery Trip chuẩn. `dp_dispatch` giữ vai trò đầu mối tương thích và chứa mã trang/API GPS.
Đây là tách module sở hữu DocType và Workspace; logic nghiệp vụ vẫn dùng các
file Python chung ở gốc package, chưa phải các thành phần triển khai độc lập.

```text
dong-phong-logistics/
├── README.md                         # Mục lục tài liệu
├── docs/
│   ├── COMMAND_README.md             # Cài đặt, build, chạy, backup, deploy
│   ├── DOC_README.md                 # Tài liệu kỹ thuật này
│   ├── PHAN_CONG.md                  # Phân công ban đầu của nhóm
│   └── THANH_VIEN_2.md               # Tài liệu thao tác nghiệp vụ
└── erpnext-local/
    ├── apps-v16.json                 # Danh sách app build vào image v16
    ├── local-v16.yaml                # Docker Compose override v16 (kèm OSRM & Optimizer)
    ├── optimizer/                    # Dịch vụ FastAPI giải bài toán VRP với Google OR-Tools
    ├── Prepare-OSRM.ps1              # Tải và xử lý dữ liệu bản đồ OpenStreetMap cho OSRM
    ├── Quan-ly-v16.ps1               # Lệnh quản lý stack v16
    ├── database/                     # Bộ cài schema/dữ liệu mẫu v15 cũ
    └── dispatch-app/
        ├── dp_dispatch/
        │   ├── dp_transport_orders/doctype/ # Đơn vận chuyển (Delivery Order)
        │   ├── dp_fleet_operations/doctype/ # Đội xe & Bảo trì (Fleet Maintenance)
        │   ├── dp_tracking_and_pod/doctype/ # Giao nhận, ePOD, GPS Log
        │   ├── dp_transport_planning/doctype/ # Kế hoạch vận chuyển (Transport Plan)
        │   ├── dp_dispatch/page/    # Nguồn JS duy nhất cho fleet-map, driver-gps
        │   ├── dp_dispatch/api/     # Nhận GPS và bộ đệm Redis
        │   ├── dp_dispatch/report/  # Báo cáo đối soát vận tải (Transport Reconciliation)
        │   ├── tracking.py          # Truy vấn theo chuyến và quyền GPS Log
        │   ├── gps_setup.py         # Schema, quyền và Page GPS
        │   ├── planning.py          # Lập lộ trình tối ưu qua OSRM & OR-Tools
        │   ├── planning_setup.py    # Schema và Workspace kế hoạch
        │   ├── accounting.py        # Tích hợp hóa đơn cước và thanh toán
        │   ├── accounting_rules.py  # Ràng buộc nghiệp vụ kế toán vận tải
        │   ├── module_navigation.py # Sáu Workspace nghiệp vụ
        │   ├── public/js/            # Client Scripts (Desk)
        │   ├── setup.py              # Custom Fields, quyền, workspace, scripts
        │   ├── hooks.py              # Frappe hooks và document events
        │   ├── validation.py         # Kiểm tra xe, Delivery Trip, tải trọng/lịch
        │   ├── api.py                # Mapping Quotation sang Delivery Order
        │   ├── delivery_confirmation.py # Xác nhận giao nhận và cập nhật trạng thái đơn
        │   ├── completion.py         # Bắt đầu và duyệt hoàn tất chuyến
        │   ├── maintenance.py        # Chi phí Vehicle Log và bảo dưỡng đội xe
        │   ├── permissions.py        # Role và phạm vi dữ liệu tài xế
        │   └── sales.py              # Ràng buộc chấp nhận báo giá
        ├── Dockerfile.v16            # Image app cho ERPNext v16
        └── Deploy-v16.ps1            # Deploy app/migrate/restart
```

## 3. Lưu schema

Schema runtime do Frappe quản lý, không tự tạo bảng bằng câu lệnh SQL:

- **DocType tùy chỉnh:** mỗi thư mục trong `dp_dispatch/<module>/doctype/<doctype>/` chứa JSON metadata, controller Python và `__init__.py`. Migration đồng bộ metadata vào database và chuyển module mà không đổi tên chứng từ.
- **Custom Fields trên DocType chuẩn:** khai báo trong `dp_dispatch/setup.py` qua `create_custom_fields`; hook `after_migrate` và `after_install` chạy hàm `dp_dispatch.setup.install`.
- **Quyền và giao diện Desk:** setup đồng bộ Role Permissions, Client Script, Workspace và Sidebar; không cần sửa source ERPNext.
- `database/install_schema.py` và `schema-reference.sql` thuộc quy trình dữ liệu v15 cũ. SQL dump chỉ để đọc/đối chiếu, không chạy để cài schema.

## 4. DocType và liên kết dữ liệu

### 4.1 DocType chuẩn được mở rộng

| DocType | Trường custom quan trọng | Ý nghĩa |
|---|---|---|
| Vehicle | `custom_payload_capacity_kg`, `custom_technical_status` | Tải trọng và trạng thái Available / Under Maintenance / Out of Service. |
| Delivery Trip | `custom_expected_end_time`, `custom_start_odometer`, `custom_end_odometer`, `custom_planned_load_kg`, `custom_total_delivery_qty`, `custom_vehicle_capacity_kg`, các trường `custom_completion_*` | Thời gian, đồng hồ km, tổng hàng/tải và quy trình tài xế yêu cầu Admin duyệt kết thúc chuyến. |
| Delivery Stop | `custom_delivery_order`, `custom_delivery_state` | Đơn vận chuyển nguồn và trạng thái tại điểm giao; giữ nguyên các trường Delivery Note/Visited chuẩn cho tương thích luồng cũ. |
| Quotation | `custom_customer_accepted`, `delivery_order` | Ghi nhận xác nhận của khách và đơn giao được tạo từ báo giá. |
| Delivery Order | `quotation` | Liên kết ngược tới báo giá nguồn. |
| Delivery Order Item | `quotation_item` | Liên kết từng dòng đơn giao với Quotation Item nguồn. |
| Vehicle Log | `custom_delivery_trip`, `custom_expense_*`, `custom_receipt`, `custom_approval_*`, `custom_review_*` | Ghi chi phí/sự cố theo chuyến và gửi Admin duyệt. |

### 4.2 DocType mới của app

- **Delivery Order** + **Delivery Order Item:** khách hàng, người gửi/nhận, địa chỉ, kiện hàng, số lượng/UOM, cân nặng, cước và trạng thái giao/cước.
- **Transport Plan** + **Transport Plan Order** + **Transport Plan Vehicle:** kế hoạch điều phối lộ trình đa xe giải bằng Google OR-Tools và OSRM.
- **Delivery Confirmation** + **Delivery Confirmation Item:** chuyến, điểm dừng, người nhận, thời gian, chứng từ và lượng phân giao/thực nhận/trả lại/còn chờ.
- **GPS Log:** tọa độ, thời điểm, xe, chuyến và mã bản tin; được tạo qua `gps_setup.py`, thuộc DP Tracking and POD.
- **Fleet Maintenance Plan:** xe, hạng mục, chu kỳ km/ngày, mốc bảo dưỡng và trạng thái giữ xe.
- **Fleet Maintenance Record:** kết quả thực hiện/nghiệm thu, số km và liên kết kế hoạch/Vehicle Log.

Các quan hệ chính:

```text
Customer → Quotation → Delivery Order → Transport Plan (OSRM + OR-Tools)
                         ↓                      ↓
                   Delivery Stop ←─────── Delivery Trip
                         ↓                      ↓
              Delivery Confirmation       Vehicle Log → Journal Entry
                         ↓                      ↓
                   Sales Invoice ←──────── Hoàn tất chuyến
                         ↓
                   Payment Entry
```

## 5. Luồng nghiệp vụ hiện có

1. **Báo giá:** nhân viên tạo Quotation cho Customer, thêm Item/Quantity/Rate, Submit. Sau khi khách xác nhận thật, đánh dấu `custom_customer_accepted`; thao tác tạo Delivery Order kiểm tra cả trạng thái Submit và cờ đồng ý.
2. **Tạo đơn giao:** tạo Delivery Order từ Quotation qua API mapping; item được liên kết với Quotation Item. Submit đơn để tạo địa chỉ giao dùng cho Delivery Stop.
3. **Lập kế hoạch & Điều phối:** điều phối viên tạo Transport Plan, chọn các đơn giao và đội xe tham gia; hệ thống tự động gọi engine OSRM và OR-Tools để tối ưu hóa lộ trình xe (VRP) theo tải trọng, vị trí và thời gian. Khi duyệt Transport Plan, hệ thống tự động sinh và Submit các Delivery Trip theo lộ trình tối ưu.
4. **Tài xế thực hiện:** tài xế chỉ đọc chuyến/đơn được giao, bắt đầu chuyến; tại điểm giao lập Delivery Confirmation và nhập kết quả hàng, người nhận, chứng từ và cước thu (nếu áp dụng).
5. **Kết thúc chuyến:** tài xế gửi yêu cầu. Admin/System Manager duyệt hoặc từ chối; việc duyệt kiểm tra xác nhận các điểm, số hàng còn chờ và điều kiện cước theo rule backend.
6. **Chi phí chuyến:** tài xế tạo Vehicle Log cho chuyến đang In Transit, nhập nhiên liệu/phí đường/phí đỗ/sửa chữa khẩn cấp/khác, chứng từ và số km. Gửi Admin/Fleet Manager duyệt. Duyệt sẽ Submit Vehicle Log; trả bổ sung yêu cầu ghi lý do và cho tài xế sửa/gửi lại; tài xế không thể tự duyệt.
7. **Bảo dưỡng:** công việc bảo dưỡng thực tế theo dõi riêng bằng Fleet Maintenance Plan/Record. Chỉ Record đã nghiệm thu và Submit mới cập nhật mốc bảo dưỡng; xe chỉ trở lại Available khi không còn kế hoạch khác đang giữ xe.
8. **Kế toán & Đối soát cước:** Chuyến hoàn tất được xuất hóa đơn cước (Sales Invoice) từ đơn vận chuyển/báo giá; tiền cước tài xế thu (COD) hoặc công nợ (Credit) được hạch toán qua Payment Entry; chi phí duyệt qua Journal Entry; đối soát toàn diện qua báo cáo Transport Reconciliation.

## 6. Validation quan trọng

- **Delivery Trip:** giờ kết thúc sau giờ xuất phát; lúc Submit cần tài xế, giờ dự kiến, tải trọng và khối lượng dương; không vượt tải; xe Available, tài xế Active và giấy phép còn hạn; chặn khoảng thời gian xung đột cho cùng xe/tài xế. Dùng khóa dòng để tuần tự hóa submit chung nguồn lực.
- **Delivery Order/Stop:** chỉ gắn đơn đã Submit; không gắn trùng/đã điều phối vào chuyến khác; khách và địa chỉ giao được lấy từ đơn; trọng lượng được backend tính lại.
- **Delivery Confirmation:** stop phải thuộc chuyến; dòng hàng đúng nguồn; lượng không âm/cân bằng và không vượt số lượng được phân; chỉ một xác nhận cuối đã Submit cho mỗi stop. Trả hàng không tự nhập kho.
- **Vehicle Log:** tài xế phải là người tạo, chuyến phải được phân công cho mình và đang In Transit, xe phải khớp; nhiên liệu cần lít/đơn giá hợp lệ; chi phí khác phải có số tiền dương; số km hiện tại không nhỏ hơn số trước. Admin/Fleet Manager xử lý trạng thái duyệt.
- **Maintenance:** xe/hạng mục/kế hoạch/Vehicle Log tham chiếu phải khớp; không chấp nhận Submit kết quả chưa nghiệm thu; kiểm tra ngày và chu kỳ bảo dưỡng.

## 7. API Frappe whitelisted

Các method dùng bằng `frappe.call` hoặc `/api/method/<dotted.path>`. Endpoint có thay đổi dữ liệu cần gọi bằng POST; quyền vẫn được kiểm tra ở backend.

| Method | Mục đích |
|---|---|
| `dp_dispatch.api.make_delivery_order_from_quotation` | Tạo/mapping Delivery Order từ Quotation đã Submit và được khách xác nhận; liên kết dòng item. |
| `dp_dispatch.delivery_confirmation.get_trip_stops` | Lấy các điểm giao của chuyến cho form xác nhận. |
| `dp_dispatch.delivery_confirmation.get_stop_details` | Lấy thông tin khách/đơn/hàng của stop đã chọn. |
| `dp_dispatch.completion.get_stop_board` | Lấy bảng tổng hợp trạng thái giao từng điểm trên Trip. |
| `dp_dispatch.completion.start_trip` | Tài xế bắt đầu chuyến được phân công. |
| `dp_dispatch.completion.request_completion` | Tài xế gửi yêu cầu kết thúc. |
| `dp_dispatch.completion.approve_completion` | Dispatcher/Admin duyệt hoàn tất sau khi đủ điều kiện. |
| `dp_dispatch.completion.reject_completion` | Dispatcher/Admin từ chối yêu cầu kết thúc, cần lý do. |
| `dp_dispatch.maintenance.get_vehicle_log_defaults` | Lấy xe, nhân viên, số km đầu từ Delivery Trip cho Vehicle Log. |
| `dp_dispatch.maintenance.send_vehicle_log_for_review` | Tài xế gửi Vehicle Log để duyệt. |
| `dp_dispatch.maintenance.review_vehicle_log` | Admin/Fleet Manager duyệt, trả sửa hoặc từ chối; ghi lý do cho trả/từ chối. |
| `dp_dispatch.permissions.assign_driver_role` | System Manager kiểm tra liên kết Driver–Employee–User và gán role DP Driver. |
| `dp_dispatch.planning.request_optimization` | Kích hoạt tối ưu hóa lộ trình xe cho Transport Plan qua engine OSRM & OR-Tools. |
| `dp_dispatch.planning.approve_transport_plan` | Duyệt kế hoạch vận chuyển, sinh và Submit các Delivery Trip tương ứng. |
| `dp_dispatch.planning.reject_transport_plan` | Từ chối kế hoạch vận chuyển với lý do bắt buộc. |
| `dp_dispatch.accounting.make_sales_invoice_for_trip` | Tạo hóa đơn bán hàng / cước vận chuyển (Sales Invoice) từ chuyến đã duyệt hoàn tất. |
| `dp_dispatch.accounting.record_delivery_payment` | Hạch toán phiếu thu cước (Payment Entry) từ xác nhận giao hàng / cước tài xế thu. |

Các controller/hooks cũng thực hiện validation trực tiếp khi lưu/Submit; không dựa riêng vào ẩn/hiện trường hoặc lọc dữ liệu client.

## 8. Quyền truy cập

- **DP Driver:** thấy chuyến/đơn được phân theo liên kết Driver → Employee → User; tạo và gửi Vehicle Log của mình; tạo xác nhận giao hàng và gửi yêu cầu kết thúc. Không thể tự duyệt log hoặc yêu cầu kết thúc.
- **Fleet Manager/System Manager:** quản lý xe, kế hoạch/kết quả bảo dưỡng và duyệt chi phí Vehicle Log. System Manager/Admin duyệt hoàn tất chuyến.
- Role cần gán cho User; việc liên kết Employee/Driver sai sẽ làm tài xế không thấy chuyến hoặc không thể tạo log.

## 9. Giới hạn và dữ liệu demo

- Đã có API nhận GPS, bộ đệm Redis, lịch sử theo chuyến và bản đồ cập nhật vị trí bằng Socket.IO, polling 3 giây dự phòng. Nguồn simulator là dữ liệu mô phỏng; chưa xác nhận kết nối thiết bị GPS vật lý qua TCP Listener. Xem [GPS_INTEGRATION](GPS_INTEGRATION.md).
- Đã hoàn thiện tính năng tối ưu tuyến bằng động cơ nội bộ OSRM (OpenStreetMap) và Google OR-Tools (không tốn chi phí Google Maps API key, đường đi thực tế theo GeoJSON). Xem [PLANNING_OSRM](PLANNING_OSRM.md).
- Đã hoàn thiện tích hợp Kế toán vận tải tự động (Sales Invoice, Payment Entry, Journal Entry và báo cáo đối soát Transport Reconciliation). Xem [ACCOUNTING_INTEGRATION](ACCOUNTING_INTEGRATION.md).
- Lịch bảo dưỡng tương lai chưa được so sánh trực tiếp với khoảng thời gian chuyến; bộ điều phối dựa trên tình trạng kỹ thuật xe hiện thời.
- Một stop chỉ hỗ trợ một xác nhận đã Submit; giao nhiều đợt cần giữ bản xác nhận Draft cho tới khi hoàn tất.
- Chi phí “Emergency Repair” ghi nhận chi phí/chứng từ; không tự tạo kế hoạch hay xác nhận bảo dưỡng.
- Site v16 đã có dữ liệu mẫu thực tế của Công ty Phân phối Đông Phong để demo nghiệp vụ và chấm điểm.
