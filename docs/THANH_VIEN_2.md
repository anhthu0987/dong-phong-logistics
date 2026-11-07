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

Kịch bản dưới đây chạy liền mạch qua bốn DocType trong phạm vi thành viên 2. `Delivery Order`, `Delivery Trip` và `Delivery Confirmation` là dữ liệu/quy trình đầu vào để tạo chuyến thật cho phần demo; không cần thay đổi code các module đó.

### Chuẩn bị một lần trước buổi demo

1. Đăng nhập tài khoản Admin, mở `Vehicle` và chọn xe demo, ví dụ biển số `43C-123.45`. Ghi lại số km hiện tại và bảo đảm trạng thái kỹ thuật đang `Available`.
2. Chuẩn bị tài khoản tài xế đã liên kết User → Employee → Driver, có Role `DP Driver`; ghi lại email đăng nhập. Chuẩn bị thêm tài khoản Admin/Fleet Manager để làm phần duyệt.
3. Tạo/chọn `Customer` và một `Item` demo. Nếu cần báo giá, chuẩn bị thêm Item Price; nếu không, tạo thẳng Delivery Order.
4. Tạo `Delivery Order` demo với một điểm giao, 10 kiện, khối lượng demo (ví dụ 4 kg/kiện), người nhận, địa chỉ và cước. Save rồi Submit.
5. Tạo `Delivery Trip` cho xe và tài xế demo, gắn Delivery Order vào Delivery Stop, rồi Submit chuyến. Kiểm tra trong tài khoản tài xế thấy đúng chuyến được giao.
6. Dùng số km và số tiền giả định nhất quán trong buổi trình bày; ghi rõ đây là dữ liệu demo, không phải định mức kỹ thuật hay chi phí thực tế.

### Module 1 — Vehicle Service Item (Hạng mục bảo dưỡng xe)

1. Dùng Search của Desk tìm **Vehicle Service Item** (có thể hiển thị tên Việt là **Hạng mục bảo dưỡng xe**); mở danh sách.
2. Nếu đã có hạng mục phù hợp, mở và dùng lại. Nếu chưa có, bấm **Add Vehicle Service Item**/**Add**, nhập tên dễ nhận biết, ví dụ `Bảo dưỡng định kỳ demo`, cùng các trường bắt buộc mà form đang hiển thị.
3. Save. Mở lại bản ghi để xác nhận hạng mục xuất hiện trong danh sách và có thể chọn ở trường `Service Item` của kế hoạch.
4. Hạng mục này chỉ mô tả loại công việc (ví dụ thay dầu, kiểm tra phanh); chu kỳ và ngày đến hạn được khai báo ở Fleet Maintenance Plan, không khai báo trùng tại đây.

### Module 2 — Fleet Maintenance Plan (Kế hoạch bảo dưỡng)

1. Mở **Kế hoạch bảo dưỡng** → **Add Fleet Maintenance Plan**.
2. Chọn xe demo và hạng mục `Bảo dưỡng định kỳ demo` vừa tạo.
3. Điền chu kỳ. Ví dụ demo: `Interval Km = 5.000`, `Interval Days = 180`. Có thể khai báo một trong hai chu kỳ, nhưng không để cả hai bằng 0.
4. Điền mốc gần nhất đã biết, ví dụ `Last Service Odometer = 45.000` và ngày bảo dưỡng gần nhất. Nếu chưa có dữ liệu thật, đánh dấu **Dữ liệu giả định cho demo** và ghi chú đây là số liệu mẫu.
5. Điền mốc kế tiếp nếu form yêu cầu/theo dõi, ví dụ `Next Service Odometer = 50.000`, ngày đến hạn; nhập ngày bắt đầu/kết thúc ngừng xe nếu đã lên lịch.
6. Để trạng thái `Planned`, Save. Mở lại kế hoạch để kiểm tra xe, hạng mục, chu kỳ và mốc đến hạn.
7. Khi xe thực sự vào xưởng, sửa kế hoạch sang `In Progress` (hoặc `Out of Service` nếu xe không được phép hoạt động) và Save. Hệ thống chuyển trạng thái kỹ thuật của xe tương ứng; xe sẽ không phù hợp để điều phối chuyến mới.

### Module 3 — Vehicle Log (Nhật ký xe, nhiên liệu và chi phí chuyến)

**Phần tài xế ghi nhận:**

1. Tài xế đăng nhập, mở Delivery Trip được giao đang `In Transit` và bấm bắt đầu chuyến theo thao tác của hệ thống.
2. Dùng Search tìm **Vehicle Log** → **New**. Chọn chuyến đang thực hiện ở trường **Chuyến vận chuyển**. Chỉ chuyến đã Submit, đang `In Transit` và được giao cho chính tài xế mới hợp lệ.
3. Kiểm tra xe, Employee và số km trước tự điền từ chuyến. Tài xế không tự đổi các giá trị liên kết này.
4. Chọn **Loại chi phí**:
   - `Fuel`: nhập `Fuel Qty` (số lít) và `Price` (đơn giá/lít); hệ thống tính `Expense Amount = số lít × đơn giá`.
   - `Road Toll`, `Parking`, `Emergency Repair` hoặc `Other`: nhập số tiền chi phí và diễn giải tương ứng.
5. Nhập Odometer (số km hiện tại, không thấp hơn số km trước), ghi mô tả, đính kèm hóa đơn/ảnh nếu có. Dùng một nhật ký cho mỗi khoản chi để Admin dễ đối chiếu.
6. Save bản nháp, sau đó bấm **Gửi Admin duyệt**. Tài xế không Submit và không tự đổi trạng thái duyệt. Trạng thái chuyển thành `Pending Review`.
7. Nếu cần ghi một khoản khác trong cùng chuyến, tạo Vehicle Log riêng cho khoản đó và lặp lại các bước trên.

**Phần Admin/Fleet Manager duyệt:**

8. Đăng nhập Admin/Fleet Manager, tìm danh sách Vehicle Log và mở bản ghi `Pending Review`.
9. Đối chiếu chuyến, xe, số km, loại chi phí, phép tính nhiên liệu, diễn giải và chứng từ đính kèm.
10. Nếu hợp lệ, bấm **Duyệt chi phí**; hệ thống chuyển trạng thái sang `Approved` và Submit nhật ký. Nếu thiếu chứng từ/thông tin, bấm **Trả lại bổ sung**, nhập ý kiến bắt buộc; tài xế sửa bản ghi `Needs Correction` rồi gửi duyệt lại. Nếu không chấp nhận, bấm **Từ chối** và ghi lý do.
11. Chỉ sau khi đã ghi các chi phí trong chuyến, tài xế gửi yêu cầu kết thúc chuyến. Admin kiểm tra xác nhận giao hàng và xử lý yêu cầu kết thúc theo quy trình chuyến. Duyệt Vehicle Log là một luồng duyệt chi phí riêng; không trình bày như điều kiện tự động để hệ thống cho kết thúc chuyến.
12. `Emergency Repair` trong Vehicle Log ghi nhận sự cố/khoản chi phát sinh. Nếu cần đưa xe vào quy trình sửa chữa và theo dõi ngày xe ngừng hoạt động, tiếp tục tạo/cập nhật Fleet Maintenance Plan và lập kết quả bảo trì; tránh ghi cùng một chi phí hai lần.

### Module 4 — Fleet Maintenance Record (Ghi nhận và nghiệm thu bảo dưỡng)

1. Sau khi xưởng hoàn thành công việc trong kế hoạch `In Progress`, Admin/Fleet Manager mở **Ghi nhận bảo dưỡng** → **Add Fleet Maintenance Record**.
2. Chọn xe. Nếu xe có kế hoạch bảo dưỡng đang hoạt động, hệ thống tự chọn kế hoạch/hạng mục khi chỉ có một lựa chọn; nếu có nhiều kế hoạch, chọn đúng kế hoạch trong hộp thoại. Có thể chọn kế hoạch trực tiếp trước, sau đó kiểm tra xe và hạng mục tự điền.
3. Xác nhận `Maintenance Plan`, `Vehicle` và `Service Item` khớp nhau. Backend sẽ từ chối nếu xe hoặc hạng mục không khớp kế hoạch.
4. Nhập ngày thực hiện, số km lúc nghiệm thu, ngày bắt đầu ngừng xe/ngày xe hoạt động lại nếu có; ghi nội dung công việc, kết quả và ghi chú.
5. Trường **Vehicle Log tham chiếu chi phí** là tùy chọn. Chỉ chọn Vehicle Log thuộc cùng xe và có dòng dịch vụ trùng hạng mục của kế hoạch. Không chọn nhật ký nhiên liệu/phí đường làm chi phí bảo trì. Nếu không có log dịch vụ phù hợp, để trống thay vì gắn sai.
6. Admin kiểm tra xe sau sửa chữa. Chỉ khi chấp nhận kết quả mới đánh dấu **Đã nghiệm thu**, đính kèm ảnh/biên bản và Save.
7. Bấm **Submit** sau khi đã nghiệm thu. Không Submit khi chưa kiểm tra/chấp nhận; hệ thống sẽ chặn.
8. Sau Submit, hệ thống cập nhật ngày và số km bảo dưỡng gần nhất, tính mốc kế tiếp từ chu kỳ, chuyển kế hoạch sang `Completed`. Xe chỉ trở lại `Available` khi không còn kế hoạch khác ở trạng thái giữ xe.

### Luồng demo xuyên suốt để trình bày

1. Admin cho xem `Vehicle Service Item` **Bảo dưỡng định kỳ demo**, rồi mở `Fleet Maintenance Plan` ở trạng thái `Planned` để minh họa xe đang có chu kỳ bảo trì.
2. Điều phối viên chuẩn bị và Submit Delivery Order/Delivery Trip cho xe demo. Tài xế đăng nhập, mở chuyến được giao và bắt đầu chuyến.
3. Tài xế giao hàng, tạo và Submit Delivery Confirmation cho điểm dừng; xác nhận này là đầu vào giao nhận của chuyến.
4. Trong chuyến, tài xế tạo Vehicle Log cho nhiên liệu và/hoặc phí đường, gửi Admin duyệt. Admin kiểm tra và duyệt hoặc trả bổ sung; trình bày trạng thái kết quả trên Vehicle Log.
5. Tài xế gửi yêu cầu kết thúc chuyến; Admin rà xác nhận giao nhận rồi duyệt kết thúc chuyến. Không nhầm thao tác này với nút duyệt Vehicle Log.
6. Nếu chuyến phát hiện xe đến hạn bảo dưỡng, Admin đưa Fleet Maintenance Plan sang `In Progress`, xác nhận xe bị giữ khỏi điều phối, đưa xe đi bảo dưỡng.
7. Admin lập Fleet Maintenance Record, đối chiếu kế hoạch, xe, hạng mục, số km và kết quả. Đánh dấu nghiệm thu, đính kèm chứng từ, Submit; mở lại kế hoạch và Vehicle để cho xem mốc bảo dưỡng mới, kế hoạch `Completed` và trạng thái xe.

**Dữ liệu demo gợi ý:** xe `43C-123.45`; hạng mục `Bảo dưỡng định kỳ demo`; chu kỳ 5.000 km/180 ngày (đánh dấu giả định); mốc trước 45.000 km, mốc kế tiếp 50.000 km; chuyến demo có nhiên liệu 20 lít × 25.000 VND/lít và phí đường 50.000 VND. Điều chỉnh theo dữ liệu trên site; không nhập số km thấp hơn mốc xe thực tế.

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
