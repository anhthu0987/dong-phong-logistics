# Tích hợp GPS với luồng vận tải — bước 4

## Phạm vi đã nối

- `Delivery Trip` là khóa chung của bản đồ, lịch sử GPS và trang tài xế. Không suy ra tuyến từ chuyến được tạo mới nhất của một xe.
- Fleet Map cho chọn chuyến đã Submit; mở từ phiếu chuyến hoặc lịch trình tài xế giữ đúng mã chuyến. Các điểm giữ `idx`, phân biệt Pickup / Delivery / Return. Thiếu tọa độ được báo rõ và không vẽ đường nối bỏ qua điểm.
- Vị trí mới nhất và lịch sử chỉ lấy GPS của chuyến đã chọn, kể cả hai chuyến dùng chung xe. Hiển thị thời gian vị trí cuối; từ 5 phút trở lên hoặc chuyến đã kết thúc được ghi là dữ liệu cũ/chuyến không chạy.
- Trang tài xế dùng `completion.start_trip`, mở form `Delivery Confirmation` dùng `get_stop_details` và cùng validate/on_submit với form chuyến, rồi gọi `completion.request_completion`. Admin duyệt bằng luồng hiện có. Có thể mở lại phiếu Draft đang nhập hoặc xem phiếu đã Submit.
- API GPS `complete_delivery_stop` cũ luôn từ chối. GPS không cập nhật `visited`, hàng trên xe hoặc Completed.
- API nhận GPS kiểm tra quyền, xe–chuyến và trạng thái In Transit. Nguồn tin không ghi mã chuyến từ simulator/điều phối được gắn khi xe có đúng một chuyến đang chạy; không có chuyến thì lưu vị trí xe không gắn chuyến; nhiều chuyến thì từ chối. Tài xế luôn phải gửi mã chuyến của mình.
- Quyền GPS Log được giới hạn cả API tùy chỉnh và truy cập DocType. Bỏ quyền đọc chung `All`; simulator chỉ gửi qua API chuyên dụng.
- Redis giữ vị trí theo chuyến; chống bản tin trùng/xung đột. Bản tin cũ không ghi lùi vị trí mới trong Redis/Vehicle. V16 có service `gps-flusher` ghi MariaDB mỗi 3 giây, scheduler phút là dự phòng.

## Cách sử dụng

1. Tải lại trình duyệt bằng Ctrl+Shift+R sau khi cập nhật.
2. Mở Workspace **DP Tracking and POD** → **Lịch trình tài xế** hoặc `/app/driver-gps` bằng tài khoản tài xế. Chọn chuyến đã Submit được phân cho mình.
3. Bấm **Bắt đầu chuyến**. Tại từng điểm bấm **Ghi nhận lấy/giao/trả**, điền thời điểm thực tế, số lượng, người giao/nhận, cước và ảnh/chứng từ nếu có; Lưu rồi Submit.
4. Quay lại Lịch trình tài xế (trang tự tải lại), kiểm tra hàng trên xe. Bấm **Gửi yêu cầu hoàn tất**. Admin mở phiếu chuyến và duyệt theo luồng cũ.
5. Mở **Bản đồ theo chuyến** hoặc `/app/fleet-map`, chọn đúng chuyến. Bấm **Lịch sử GPS** để vẽ tối đa 3.000 điểm mới nhất của riêng chuyến đó.
6. Chuyến cũ Completed dùng để xem lại. Để kiểm thử bắt đầu/lấy/giao, tạo chuyến mới đã Submit. Chưa có GPS hoặc tọa độ điểm thì bản đồ sẽ thông báo thiếu dữ liệu, không tự tạo tọa độ.

## Kiểm thử

Chạy trong thư mục bench sites (v16), bằng Python của bench:

```powershell
docker exec -w /home/frappe/frappe-bench/sites logistics-erpnext-v16-backend-1 /home/frappe/frappe-bench/env/bin/python ../apps/dp_dispatch/tests/gps_transport_integration.py
```

Bài kiểm thử dùng MariaDB thật, Redis namespace riêng, dữ liệu nghiệp vụ rollback sau chạy. Bao gồm GPS cùng xe/khác chuyến, quyền API và DocType, thứ tự lấy–giao, bản tin cũ/trùng/xung đột, API cũ bị chặn, chuyến Completed bị chặn gửi GPS; đồng thời chạy lại toàn bộ acceptance vận tải (thu cước, hàng trên xe, trả hàng, duyệt hoàn tất). Không gửi SMS/email hay hạch toán thanh toán.

Kết quả chạy lưu tại `docs/gps-integration-results.json`. Giao diện được kiểm tra cú pháp JavaScript và nội dung page qua HTTP; chưa xác nhận thao tác xuyên suốt bằng trình duyệt vì công cụ computer-use dừng khi không xác định được URL Chrome.

## Ranh giới với các bước sau

- Nét đứt trên bản đồ là **sơ đồ thứ tự điểm**, chưa phải hình dạng tuyến đường đã được Maps API tính. Không dùng sơ đồ này để kết luận lệch tuyến.
- Giao diện cập nhật bằng polling 3 giây, chưa triển khai sự kiện vị trí qua Socket.IO.
- Thiết bị GPS TCP Listener, xác thực thiết bị phần cứng, phát hiện lệch tuyến, AI/OR-Tools, phê duyệt tái tối ưu và Zalo/SMS là các phần tiếp theo trong kiến trúc, chưa nằm trong lần nối bước 4.
- Nguồn GPS hiện có là HTTP API/simulator. Trang tài xế phục vụ thao tác giao nhận, không tự thu vị trí điện thoại.
