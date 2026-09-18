# Hướng dẫn triển khai – thành viên 2 và 3

**Đề tài:** Quản trị và điều phối Logistics & Vận tải liên vùng.  
**Doanh nghiệp mô phỏng:** Công ty Phân phối Đông Phong (DP).  
**Phạm vi:** Mô phỏng giữa kỳ trên ERPNext; GPS dùng tọa độ giả lập, không cần phần cứng.

## 1. Điểm xuất phát chung

Nhóm dùng ERPNext và Frappe HR. Backend bổ sung viết bằng Python/Frappe; giao diện bổ sung dùng JavaScript. Ưu tiên chức năng và biểu mẫu sẵn có, chỉ code phần còn thiếu.

Tại thời điểm bàn giao đã có:

| Nội dung | Dữ liệu / trạng thái |
|---|---|
| Công ty | Công ty Phân phối Đông Phong, viết tắt DP |
| Xe | 51C-123.45, 51C-234.56, 51C-345.67 |
| Tài xế | HR-DRI-2026-00001, HR-DRI-2026-00002, HR-DRI-2026-00003 |
| Chuyến mẫu | MAT-DT-2026-00001, trạng thái Draft |
| Điểm giao mẫu | Có Customer và Address mang tiền tố DP DEMO |
| Code điều phối | App `dp_dispatch`: kiểm tra lịch, tình trạng xe/tài xế, tải trọng, thời gian và số km |
| Giao nhận, chi phí, bảo trì, GPS | Chưa triển khai phần bổ sung; chưa có demo xuyên suốt |

Đây là mã dữ liệu của máy chủ hiện tại; khi tạo môi trường khác phải lấy mã thực tế từ hệ thống, không gắn cứng mã mẫu vào code.

### Cách làm việc

1. Thành viên 1 quản lý bản chạy chung và ghép thay đổi. Thành viên 2, 3 phụ trách cả cấu hình, code, dữ liệu mẫu và hướng dẫn demo cho phần mình.
2. Phát triển trong custom app hoặc cấu hình có thể xuất và cài lại. Không sửa trực tiếp mã nguồn `frappe`, `erpnext`, `hrms`; không tạo bảng bằng SQL thủ công.
3. Mỗi người làm nhánh riêng: đề xuất `feature/operations` và `feature/gps`. Nhóm chưa tạo repository chung; thống nhất repository trước khi trao đổi code.
4. Đọc xe và chuyến đã có. Không tạo lại bảng Vehicle, Driver, Delivery Trip. Không tự đổi tên trường hoặc mã bản ghi mà thành viên khác đang dùng.
5. Bàn giao mã nguồn và script/fixtures cài đặt, không chỉ ảnh chụp hoặc cấu hình trên một máy. Các app mới phải được thêm vào image và các worker khi tích hợp.
6. Máy bạn khác không dùng `localhost:8085` của máy chủ. Khi cùng quán, cần cấu hình truy cập LAN và tài khoản riêng; Wi-Fi quán có thể chặn các máy truy cập nhau. Hiện cổng ERPNext vẫn chỉ mở trên localhost, kết nối LAN chưa được cấu hình.

## 2. Thành viên 2 – giao nhận, nhiên liệu và bảo trì

### Mục tiêu bàn giao

Thực hiện được việc xuất hàng, ghi kết quả nhận hàng, ghi nhiên liệu/dịch vụ xe và theo dõi bảo trì cho xe, chuyến dùng chung. Giao diện có thể tận dụng biểu mẫu ERPNext; không bắt buộc xây website riêng.

### Bước 1 – khảo sát phần chuẩn trước khi tạo thêm

Mở và thử các DocType: Item, Warehouse, Sales Order, Delivery Note, Vehicle Log, Vehicle Service và Vehicle Service Item. Ghi lại: chức năng nào dùng được ngay, cần thêm trường nào, cần code quy tắc nào.

Không tạo Fuel Log riêng. Nhiên liệu và chi phí dịch vụ dùng Vehicle Log cùng bảng con Vehicle Service. Maintenance Schedule chuẩn không mặc định thay thế được kế hoạch bảo trì đội xe theo km/ngày; cần đối chiếu trước.

### Bước 2 – dựng luồng giao hàng chuẩn

- Chuẩn bị 2 mặt hàng, kho thuộc DP và tồn kho mẫu đủ để xuất. Dùng chứng từ kho hợp lệ để nhập tồn, không sửa số lượng trực tiếp trong database.
- Tạo đơn bán mẫu nếu sử dụng luồng Sales Order, rồi tạo Delivery Note và dòng hàng.
- Gắn Delivery Note vào đúng Delivery Stop của chuyến mẫu khi chuyến còn cho phép chỉnh sửa. Phối hợp thành viên 1 trước khi Submit.
- Kiểm tra hàng, số lượng, khách hàng, kho và công ty thống nhất giữa các chứng từ.

### Bước 3 – bổ sung xác nhận giao nhận khi phần chuẩn chưa đáp ứng

Theo thiết kế, dự kiến có:

| Cấu trúc | Thông tin tối thiểu |
|---|---|
| Delivery Confirmation | Chuyến, tham chiếu điểm giao, thời gian nhận, người nhận, tệp bằng chứng, các dòng xác nhận |
| Delivery Confirmation Item (bảng con) | Tham chiếu dòng Delivery Note Item, lượng phân giao, thực nhận, trả lại và còn chờ |

Quy tắc cần code phía máy chủ:

- Điểm giao phải thuộc chuyến đã chọn; dòng hàng phải thuộc Delivery Note của điểm giao đó.
- Các số lượng không âm, dùng cùng đơn vị của dòng hàng nguồn; lượng phân giao = thực nhận + trả lại + còn chờ.
- Không được cộng các lần xác nhận làm vượt số lượng được phân giao. Chọn rõ một cách quản lý: một xác nhận hiện hành cho mỗi điểm giao, hoặc nhiều lần xác nhận với kiểm tra cộng dồn.
- Ghi số lượng trả lại trong xác nhận không tự làm tăng tồn kho. Nếu hàng thực sự nhập lại kho, xử lý bằng chứng từ trả hàng phù hợp và liên kết để đối chiếu.
- `Delivery Stop.visited` chỉ phản ánh đã ghé điểm; không thay cho bằng chứng nhận đủ hàng. Không tự đánh dấu hoàn tất tất cả điểm giao chỉ để kết thúc demo.

Ví dụ mô phỏng: phân giao 10 thùng, khách nhận 8, trả lại 2, còn chờ 0. Demo phải giải thích được 2 thùng trả lại được xử lý thế nào.

### Bước 4 – nhiên liệu và chi phí

- Dùng Vehicle Log ghi xe, ngày, số km, lượng nhiên liệu, đơn giá và chứng từ.
- Bổ sung `custom_delivery_trip` kiểu Link → Delivery Trip khi cần gắn chi phí với chuyến. Trường này chưa được thành viên 1 tạo.
- Kiểm tra xe trong Vehicle Log trùng xe của chuyến liên kết. Tuân theo quy tắc số km có sẵn; không sửa đồng hồ xe trực tiếp để vượt lỗi.
- Tách chi phí nhiên liệu và dịch vụ để tổng hợp; không ghi lại một khoản chi ở cả Vehicle Log và một bảng bảo trì khác.
- Chỉ tính tiêu hao khi có đủ dữ liệu quãng đường và mức nhiên liệu thích hợp; không lấy lượng vừa đổ làm lượng tiêu hao thực tế một cách mặc định.

### Bước 5 – kế hoạch và kết quả bảo trì

Nếu cần cấu trúc bổ sung, triển khai Fleet Maintenance Plan và Fleet Maintenance Record như thiết kế: xe, hạng mục, chu kỳ km/ngày, mốc lần trước, mốc kế tiếp, khoảng giữ xe, ngày thực hiện và nghiệm thu. Record tham chiếu Vehicle Log để dùng lại chi phí.

- Chu kỳ phải hợp lệ; ngày kết thúc giữ xe không trước ngày bắt đầu.
- Kết quả và nhật ký dịch vụ phải thuộc đúng xe của kế hoạch.
- Chỉ cập nhật mốc bảo trì sau khi có kết quả được nghiệm thu. Chu kỳ demo phải ghi là giả định.
- Dùng lại `Vehicle.custom_technical_status`: Available / Under Maintenance / Out of Service. Thống nhất với thành viên 1 thời điểm đổi trạng thái; không tự trả xe về Available nếu vẫn còn công việc bảo trì chưa kết thúc.
- Phiên bản điều phối hiện tại kiểm tra trạng thái xe, chưa tự kiểm tra khoảng bảo trì trong tương lai. Muốn ghép chức năng này phải phối hợp thành viên 1.

### Các ca phải tự kiểm tra

| Ca | Kết quả mong đợi |
|---|---|
| Giao đủ | Ghi nhận đúng số lượng và bằng chứng |
| Giao thiếu / trả hàng | Có đối chiếu lượng còn lại, không tự cộng tồn sai |
| Chọn dòng hàng của điểm giao khác | Bị chặn phía máy chủ |
| Số lượng âm hoặc xác nhận vượt nguồn | Bị chặn |
| Ghi nhiên liệu cho sai xe của chuyến | Bị chặn |
| Bảo trì và nghiệm thu | Lưu được lịch sử, dùng lại chi phí, trạng thái xe phù hợp |

### Sản phẩm bàn giao

1. Code/cấu hình cài lại được cho các trường và DocType thực sự cần bổ sung.
2. Bộ dữ liệu demo giao đủ, giao thiếu/trả hàng, nhiên liệu và bảo trì.
3. Danh sách ca đã thử, kết quả và các giới hạn còn lại.
4. Hướng dẫn thao tác kèm ảnh ngắn; danh sách trường API cho phần điều phối cần đọc.

Chưa triển khai cổng thanh toán/COD hoặc AI trong phần giữa kỳ này.

## 3. Thành viên 3 – GPS giả lập và bản đồ

### Mục tiêu bàn giao

Xe di chuyển trên bản đồ theo tọa độ giả lập; dữ liệu được gửi về backend, lưu lại và xem được lịch sử theo xe/chuyến. Thành viên 3 làm trọn phần GPS: cấu trúc dữ liệu, backend, chương trình giả lập và giao diện.

### Bước 1 – tạo GPS Log

Đây là DocType bổ sung chưa được tạo, không phải bảng GPS chuẩn của ERPNext.

| Trường đề xuất | Kiểu Frappe | Yêu cầu |
|---|---|---|
| vehicle | Link → Vehicle | Bắt buộc |
| delivery_trip | Link → Delivery Trip | Có thể trống ở mức lưu vị trí xe; demo theo chuyến phải có |
| recorded_at | Datetime | Thời điểm vị trí được ghi nhận |
| latitude | Float | Từ -90 đến 90 |
| longitude | Float | Từ -180 đến 180 |
| source_event_id | Data, Unique | Mã duy nhất toàn hệ thống, gồm tiền tố nguồn/lần chạy |
| source_type | Select | Mặc định Simulated trong giữa kỳ |

Khóa chính `name` do Frappe quản lý. Đề xuất index `(vehicle, recorded_at)` và `(delivery_trip, recorded_at)` để truy vấn lịch sử. Thống nhất múi giờ với site; nếu bản tin dùng UTC phải chuyển đổi rõ ràng, không lưu lẫn giờ UTC và giờ Việt Nam.

### Bước 2 – API tiếp nhận và truy vấn

- Viết endpoint Python/Frappe nhận bản tin qua POST, có xác thực. Không dùng tài khoản Administrator hoặc nhúng mật khẩu/token vào JavaScript giao diện.
- Kiểm tra quyền, xe tồn tại, chuyến tồn tại và xe đúng với chuyến. Kiểm tra tọa độ là số hữu hạn, thời gian hợp lệ và loại nguồn.
- Gửi lại cùng `source_event_id` và cùng nội dung không được tạo dòng mới. Cùng ID nhưng nội dung khác phải báo xung đột.
- Vị trí mới nhất chọn theo `recorded_at`, không theo thứ tự bản tin tới, để bản tin chậm không kéo biểu tượng xe lùi lại.
- API lịch sử lọc theo xe/chuyến và thời gian, có phân trang/giới hạn. Không trả toàn bộ bảng cho mọi lần cập nhật.
- Kiểm tra quyền đọc trên xe/chuyến và dữ liệu GPS. Nếu sử dụng get_all hoặc SQL phải tự kiểm tra quyền tương ứng; không chỉ kiểm tra đã đăng nhập.

Ví dụ bản tin, tên endpoint do thành viên 3 chốt khi triển khai:

```json
{
  "vehicle": "51C-123.45",
  "delivery_trip": "MAT-DT-2026-00001",
  "recorded_at": "2026-09-18 08:00:00",
  "latitude": 10.7769,
  "longitude": 106.7009,
  "source_event_id": "sim-run-001-point-001",
  "source_type": "Simulated"
}
```

Ngày giờ và tọa độ trên chỉ là ví dụ. Khi demo dùng thời gian của lần chạy; không gửi mã chuyến/xe ví dụ nếu môi trường không có bản ghi tương ứng.

### Bước 3 – chương trình giả lập

- Chuẩn bị khoảng 20–50 điểm trên một tuyến mô phỏng, có thứ tự.
- Cho chọn xe, chuyến, khoảng gửi và mã lần chạy. Đề xuất gửi mỗi 5–10 giây để dễ quan sát.
- Có bắt đầu/dừng, thông báo lỗi và gửi lại khi mất kết nối; gửi lại phải giữ mã bản tin cũ.
- Đọc URL và thông tin xác thực từ cấu hình riêng không đưa lên Git.
- Không cần thiết bị GPS, điện thoại hay AI để hoàn thành phần này.

### Bước 4 – giao diện trong ERPNext

Tạo trang GPS bằng JavaScript trong custom app, dùng bản đồ và nguồn bản đồ phù hợp. Thống nhất thư viện/nhà cung cấp, điều kiện sử dụng và hiển thị nguồn trước khi triển khai. Không bắt buộc React hoặc frontend độc lập.

Giao diện tối thiểu có:

- Bộ chọn xe và chuyến.
- Biểu tượng vị trí mới nhất và đường lịch sử của xe đã chọn.
- Tọa độ, thời gian cập nhật cuối và nhãn **Dữ liệu giả lập**.
- Trạng thái chưa có dữ liệu / đang cập nhật / lâu chưa nhận bản tin. Ngưỡng cảnh báo phải cấu hình hoặc ghi rõ là giả định demo.
- Tự cập nhật theo chu kỳ. Polling là đủ cho demo; không bắt buộc WebSocket.

Không tự đổi `Delivery Stop.visited`, xác nhận khách nhận hàng hoặc trạng thái Completed chỉ vì GPS tới gần điểm giao.

### Các ca phải tự kiểm tra

| Ca | Kết quả mong đợi |
|---|---|
| Bản tin hợp lệ | Lưu, hiển thị đúng xe/chuyến |
| Vĩ độ/kinh độ sai | Bị chặn |
| Xe không thuộc chuyến | Bị chặn |
| Gửi trùng bản tin | Chỉ một bản ghi, hoặc báo xung đột nếu khác nội dung |
| Bản tin đến chậm | Không thay vị trí mới nhất bằng điểm cũ |
| Dừng bộ giả lập | Hiển thị thời điểm cập nhật cuối và trạng thái phù hợp |
| Chuyển xe/chuyến | Không trộn lịch sử |
| Không đăng nhập / thiếu quyền | Không đọc hoặc ghi được dữ liệu không được phép |

### Sản phẩm bàn giao

1. Custom app/cấu hình GPS Log và API có thể cài lại.
2. Chương trình giả lập cùng tuyến mẫu, hướng dẫn chạy và dừng.
3. Trang bản đồ trong ERPNext.
4. Tài liệu API: endpoint, xác thực, request/response, lỗi và quy ước thời gian.
5. Kết quả kiểm thử và một video/chuỗi ảnh ngắn của demo xe di chuyển.

## 4. Thứ tự ghép bài demo của cả nhóm

1. Thành viên 1 chuẩn bị xe, tài xế, giờ chuyến và tải trọng mô phỏng.
2. Thành viên 2 chuẩn bị hàng, kho, khách/địa chỉ và Delivery Note; phối hợp gắn phiếu vào điểm giao trước khi chốt chuyến.
3. Thành viên 1 kiểm tra và Submit chuyến hợp lệ.
4. Thành viên 3 chạy bộ giả lập, hiển thị vị trí và lịch sử theo đúng chuyến đó.
5. Thành viên 2 ghi kết quả giao nhận, nhiên liệu và đối chiếu hàng còn lại; phân biệt kết quả nhận hàng với trạng thái đã ghé điểm.
6. Cả nhóm kiểm tra liên kết dữ liệu, xử lý các phần còn chờ và giải thích kết quả demo.

**Mốc hoàn thành:** mỗi người chạy được phần mình trên môi trường thử; sau đó thành viên 1 tích hợp code/cấu hình lên bản chung và cả nhóm chạy lại một luồng hoàn chỉnh. Việc có đủ bảng trong sơ đồ chưa có nghĩa đã hoàn thành các bước nghiệp vụ.
