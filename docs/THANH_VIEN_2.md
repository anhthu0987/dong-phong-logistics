# Thành viên 2 – giao nhận, nhiên liệu và bảo trì

Phần này bổ sung vào app `dp_dispatch`, tương thích site ERPNext v16 độc lập ở `http://localhost:8086`. Không chạy trên site/database v15.

> Hướng dẫn thao tác này được cập nhật theo code tích hợp hiện tại. Nếu nội dung cũ khác với quy tắc/schema hiện tại, xem [DOC_README](DOC_README.md) về kiến trúc và [COMMAND_README](COMMAND_README.md) về lệnh triển khai.

## Phần được bổ sung

- `Delivery Confirmation` và bảng con `Delivery Confirmation Item`: lưu xác nhận giao nhận, người nhận, thời điểm và tệp bằng chứng. Mỗi điểm giao chỉ có một xác nhận đã Submit; mỗi dòng tham chiếu chính xác một dòng `Delivery Order Item` (hoặc `Delivery Note Item` ở luồng chứng từ cũ).
- Validation phía máy chủ xác nhận điểm dừng thuộc chuyến, phiếu nguồn thuộc điểm dừng, số lượng không âm, cân bằng `phân giao = thực nhận + trả lại + còn chờ`, và tổng phân giao không vượt lượng phiếu xuất. Tác vụ đồng thời được tuần tự hóa bằng khóa dòng chuyến và dòng hàng.
- Trả lại trong `Delivery Confirmation` chỉ là ghi nhận nghiệp vụ. Muốn nhập kho, phải tạo Delivery Note trả hàng bằng chức năng `Create > Return` của ERPNext và liên kết/đối chiếu với xác nhận.
- `Vehicle Log.custom_delivery_trip` liên kết chi phí với chuyến. Tài xế chọn chuyến `In Transit`, nhập chi phí/chứng từ và gửi duyệt; Admin/Fleet Manager duyệt, trả bổ sung hoặc từ chối. Nhiên liệu dùng `fuel_qty`/`price`; phí đường, đỗ, sửa chữa khẩn cấp và khác có trường tiền/diễn giải riêng. Nhật ký được Submit sau khi Admin duyệt.
- `Fleet Maintenance Plan` lưu xe, hạng mục dịch vụ, chu kỳ km/ngày, mốc trước/kế tiếp và khoảng giữ xe. `Fleet Maintenance Record` tham chiếu kế hoạch và Vehicle Log, chỉ cập nhật mốc sau khi nghiệm thu và Submit.
- Kế hoạch `In Progress`/`Out of Service` cập nhật `Vehicle.custom_technical_status`; hoàn tất bảo trì chỉ trả xe về `Available` sau khi nghiệm thu và không còn kế hoạch đang giữ xe.

Role `DP Driver` được app cấp quyền giới hạn theo tài xế cho chuyến, đơn giao, xác nhận và Vehicle Log. Tài khoản tài xế cần liên kết User → Employee → Driver và được gán role. Admin/System Manager hoặc Fleet Manager xử lý duyệt chi phí; Admin/System Manager duyệt kết thúc chuyến.

## Quyết định luồng nghiệp vụ

- Luồng giao thường dùng `Delivery Order` của `dp_dispatch`; không cần tạo `Sales Order`, `Delivery Note`, `Stock Entry` hoặc Warehouse chỉ để giao kiện. Nếu muốn báo giá, có thể đi `Quotation` → khách xác nhận → `Delivery Order`.
- Khi Submit Delivery Order, app tạo/liên kết địa chỉ giao ERPNext để Delivery Stop có địa chỉ hợp lệ. Đơn được gắn vào một điểm dừng trên chuyến.
- `Delivery Note` chỉ được hỗ trợ như nguồn tương thích với chứng từ cũ; không phải bước bắt buộc trong luồng mặc định.
- Số lượng trả/hoàn trong Delivery Confirmation là ghi nhận giao nhận; không tự cộng tồn kho. Nếu cần nhập hàng trả về kho, phải làm chứng từ kho phù hợp riêng.
- Cước thu khi giao là dữ liệu vận hành có người thu, thời điểm và phương thức; chưa tự sinh hóa đơn/kế toán. Cước vận chuyển khác với COD (tiền thu hộ giá trị hàng).

## Cập nhật lên site v16

Mở PowerShell tại `dong-phong-logistics/erpnext-local`, bảo đảm Docker Desktop báo Engine running, rồi chạy:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\dispatch-app\Deploy-v16.ps1
```

Script sao lưu site v16 trước, build image app, cài app nếu chưa có, chạy `bench migrate` và khởi động lại dịch vụ. Backup được lưu trong `erpnext-local/backups-v16/`. Không sửa hay trỏ sang database v15.

Sau đó mở Desk, hard refresh (Ctrl+F5), tìm `Delivery Confirmation`, `Fleet Maintenance Plan`, `Fleet Maintenance Record` hoặc `Vehicle Log`. Tài xế cần role DP Driver; Admin/Fleet Manager thấy các thao tác duyệt.

## Luồng thao tác demo

### 1. Tạo đơn vận chuyển

1. Tạo/chọn Customer và Item demo. Nếu cần báo giá, tạo Item Price phù hợp để Quotation lấy được đơn giá.
2. Tạo `Delivery Order` trực tiếp hoặc tạo từ Quotation đã Submit và khách đã xác nhận đồng ý.
3. Điền thông tin người gửi/nhận, số điện thoại, địa chỉ lấy/giao, thời gian yêu cầu, dòng hàng/mô tả, số lượng, đơn vị và khối lượng mỗi kiện. Nhập cước vận chuyển và bên trả cước.
4. Save rồi Submit Delivery Order. App tạo/liên kết Address ERPNext từ địa chỉ giao; không cần tạo Warehouse hay nhập tồn chỉ để mô phỏng giao kiện.
5. Mở Delivery Trip còn chỉnh sửa, thêm Delivery Stop và chọn đơn đã Submit. Khách hàng/địa chỉ tự điền; phối hợp điều phối kiểm tra tải trọng rồi Submit chuyến.
6. Nếu demo chứng từ kho ERPNext cũ, có thể dùng `Delivery Note` đã Submit làm nguồn thay thế cho stop; đó là luồng tương thích, không phải luồng giao mặc định.

### 2. Xác nhận giao hàng

1. Mở `Delivery Confirmation` > New; chọn Delivery Trip được phân công.
2. Chọn Delivery Stop của chuyến. Đơn giao và cước cần thu tự điền từ điểm dừng.
3. Nhập thời điểm, người nhận và đính kèm ảnh/chứng từ nếu có.
4. Bảng kết quả tự nạp các dòng `Delivery Order Item`; nhập lượng phân giao, thực nhận, trả lại và còn chờ. Với stop dùng chứng từ kho cũ, nguồn sẽ là `Delivery Note Item`.
5. Ví dụ 10 thùng: phân giao 10, nhận 8, trả lại 2, còn chờ 0. Save rồi Submit.
6. Nếu 2 thùng trả lại thật sự về kho, tạo Delivery Note Return từ phiếu gốc; xác nhận không tự cộng kho.
7. Đánh dấu `Visited` trên Delivery Stop chỉ thể hiện xe đã ghé, không thay bằng chứng giao hàng.

### 3. Nhật ký nhiên liệu và chi phí

1. Tài xế mở `Vehicle Log` > New khi chuyến được phân công đang `In Transit`; chọn chuyến. Hệ thống điền xe, Employee và số km khởi hành.
2. Chọn `Fuel`, nhập số lít/đơn giá; hoặc chọn `Road Toll`, `Parking`, `Emergency Repair`, `Other` và nhập số tiền. Bổ sung diễn giải, chứng từ/ảnh và số km hiện tại.
3. Save rồi chọn **Gửi Admin duyệt**. Không tự Submit. Nếu khoản chi không thuộc chuyến đang chạy, không dùng luồng Vehicle Log của tài xế này.
4. Admin/Fleet Manager mở nhật ký chờ duyệt: **Duyệt chi phí** sẽ duyệt và Submit; **Trả lại bổ sung**/**Từ chối** cần ghi lý do. Tài xế sửa và gửi lại nếu trạng thái là `Needs Correction`.
5. `Emergency Repair` chỉ ghi nhận khoản chi/sự cố. Nếu có công việc sửa chữa/bảo dưỡng cần theo dõi, Admin lập Fleet Maintenance Plan/Record riêng; tránh ghi trùng khoản chi.

### 4. Lập kế hoạch và nghiệm thu bảo trì

1. Tạo Vehicle Service Item nếu chưa có.
2. Tạo `Fleet Maintenance Plan`: chọn xe/hạng mục, nhập chu kỳ km hoặc ngày, mốc đã biết, ngày giữ xe và ghi `Demo Assumption` nếu số liệu giả định.
3. Chuyển kế hoạch sang `In Progress` khi xe vào bảo trì; trạng thái xe chuyển `Under Maintenance`, nên thành viên 1 không thể phân chuyến.
4. Khi hoàn thành, tạo `Fleet Maintenance Record` từ kế hoạch; chọn cùng xe/hạng mục. Có thể tham chiếu Vehicle Log chứa dòng dịch vụ tương ứng.
5. Nhập ngày, Odometer, thời gian giữ xe; xác nhận nghiệm thu, đính kèm biên bản nếu có, rồi Submit. Mốc kế tiếp được tính từ chu kỳ; xe chỉ về `Available` khi không còn kế hoạch bảo trì đang giữ.

## Ca kiểm soát để trình bày

| Thao tác | Kết quả mong đợi |
|---|---|
| Đủ số lượng và có bằng chứng | Lưu/Submit xác nhận được |
| Chọn stop không thuộc trip | Backend từ chối |
| Chọn dòng hàng không thuộc Delivery Order/Delivery Note của stop | Backend từ chối |
| Số lượng âm hoặc phép cộng không cân | Backend từ chối |
| Phân giao vượt lượng nguồn, kể cả xác nhận khác | Backend từ chối |
| Tạo xác nhận thứ hai đã Submit cho cùng stop | Backend từ chối |
| Tài xế chọn chuyến không phải của mình hoặc chuyến không In Transit | Backend từ chối |
| Vehicle Log liên kết trip có xe khác / nhiên liệu thiếu số lít hoặc đơn giá | Backend từ chối |
| Tài xế tự đổi trạng thái duyệt hoặc tự Submit | Backend từ chối |
| Kết quả bảo trì khác xe/hạng mục kế hoạch hoặc Vehicle Log sai xe/dịch vụ | Backend từ chối |
| Kết thúc giữ xe trước ngày bắt đầu | Backend từ chối |
| Submit kết quả chưa nghiệm thu | Backend từ chối; mốc bảo trì không đổi |

Các ca trên là tiêu chí kiểm tra; chưa chạy bộ test tự động trong lần bổ sung này. Bộ dữ liệu hàng, tồn kho, khách hàng, địa chỉ và chứng từ cần được tạo trên từng site bằng giao diện ERPNext.

## API fields cho phần điều phối

- `Delivery Trip`: `name`, `vehicle`, `driver`, `departure_time`, `custom_expected_end_time`, `custom_start_odometer`, `custom_end_odometer`, `custom_planned_load_kg`, `status`, `delivery_stops[].name`, `delivery_stops[].custom_delivery_order`, `delivery_stops[].delivery_note`, `delivery_stops[].visited`.
- `Delivery Stop`: `custom_delivery_order`, `delivery_note`, `customer`, `address`, `visited`.
- `Delivery Order`: `name`, `customer`, `sender_name`, `sender_phone`, `pickup_address`, `recipient_name`, `recipient_phone`, `delivery_address`, `delivery_date`, `items[].item_code`, `items[].qty`, `items[].uom`, `items[].weight_kg`, `shipping_fee`, `fee_payer`, `delivery_status`.
- `Delivery Confirmation`: `name`, `delivery_trip`, `delivery_stop`, `delivery_order` (hoặc `delivery_note` trong luồng cũ), `received_at`, `recipient`, `proof_file`, `items[].delivery_order_item_ref` (hoặc `delivery_note_item_ref`), `items[].uom`, `items[].allocated_qty`, `items[].delivered_qty`, `items[].returned_qty`, `items[].pending_qty`, `docstatus`.
- `Vehicle`: `name`, `license_plate`, `custom_payload_capacity_kg`, `custom_technical_status`.
- `Vehicle Log`: `name`, `license_plate`, `custom_delivery_trip`, `date`, `odometer`, `last_odometer`, `fuel_qty`, `price`, `invoice`, `service_detail[].service_item`, `service_detail[].expense_amount`.
- `Fleet Maintenance Plan`: `name`, `vehicle`, `service_item`, `interval_km`, `interval_days`, `last_service_odometer`, `last_service_date`, `next_service_odometer`, `next_service_date`, `hold_start`, `hold_end`, `status`.
- `Fleet Maintenance Record`: `name`, `maintenance_plan`, `vehicle`, `service_item`, `vehicle_log`, `work_date`, `odometer`, `accepted`, `docstatus`.

## Giới hạn hiện tại

- Chưa tự tạo dữ liệu mẫu; chưa dùng API Google Maps, GPS, AI, eSMS/Zalo.
- Trạng thái `Visited` và xác nhận giao nhận là hai dữ liệu riêng.
- Bảo trì trong tương lai chưa được tích hợp vào kiểm tra lịch điều phối; chỉ xe có trạng thái kỹ thuật không phải `Available` bị chặn.
- Giá trị chu kỳ mẫu phải được đánh dấu giả định, không xem như khuyến nghị kỹ thuật cho xe thật.
