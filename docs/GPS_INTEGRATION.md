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

Kết quả chạy lưu tại `docs/gps-integration-results.json`. Ngày 09/11/2026 đã thao tác trên trình duyệt bằng tài khoản tài xế: bắt đầu chuyến, mở bản đồ/lịch sử GPS, lập và Submit phiếu lấy/giao, gửi yêu cầu hoàn tất; sau đó dùng admin gửi duyệt. Kết quả cuối xác nhận trực tiếp từ database vì công cụ trình duyệt bị tắt trước lần chụp cuối.

## Ranh giới với các bước sau

- Nét đứt trên bản đồ là **sơ đồ thứ tự điểm**, chưa phải hình dạng tuyến đường đã được Maps API tính. Không dùng sơ đồ này để kết luận lệch tuyến.
- Vị trí mới được đẩy qua Socket.IO; polling 3 giây chỉ là dự phòng khi mất kết nối. Snapshot 30 giây đối soát trạng thái chuyến/quyền và gia hạn theo dõi.
- Thiết bị GPS TCP Listener, xác thực thiết bị phần cứng, phát hiện lệch tuyến, AI/OR-Tools, phê duyệt tái tối ưu và Zalo/SMS là các phần tiếp theo trong kiến trúc, chưa nằm trong lần nối bước 4.
- Nguồn GPS hiện có là HTTP API/simulator. Trang tài xế phục vụ thao tác giao nhận, không tự thu vị trí điện thoại.


## Nghiệm thu simulator và giao diện ngày 09/11/2026

- Đã backup, build và migrate stack v16; giữ nguyên dữ liệu site.
- Chuyến `MAT-DT-2026-00002`, đơn `DP-DO-2026-00002`, xe `51D-728.46`, tài xế Trần Quang Minh, khách Bao bì Nam Phước.
- Simulator có sẵn gửi 20/20 điểm qua HTTP API bằng tài khoản có role DP GPS Simulator; flusher lưu đủ 20 GPS Log. Vị trí cuối: 10.9804, 106.6519. Bản đồ và đường lịch sử hiển thị đúng chuyến.
- Phiếu lấy `DP-DC-2026-00003`: 40 kiện / 240 kg. Phiếu giao `DP-DC-2026-00004`: giao đủ, ghi nhận cước 600.000 VND. Hai phiếu đều Submit.
- Kết quả cuối: chuyến Completed/Approved, hàng trên xe 0 kg, đơn Delivered/Paid. Đây là dữ liệu dựng để nghiệm thu; không phát sinh thanh toán hay hạch toán thực tế.
- Tài khoản API tạm đã vô hiệu hóa, thu hồi key và xóa cấu hình bí mật sau kiểm tra.
- Các lỗi đã sửa: thiếu metadata Page khiến migration thay JS bằng trang mẫu; nhận nhầm namespace L là Leaflet đã tải; Client Script bị nạp trùng; Deferred không hỗ trợ finally; route mặc định không nạp hàng nguồn; yêu cầu hoàn tất làm mất trạng thái In Transit.
- Kiểm thử hồi quy giao diện: `node erpnext-local/dispatch-app/tests/test_frontend_regressions.js`. Bộ GPS/vận tải và 4 bài kiểm thử simulator đều đạt sau sửa.
- Lỗi Socket.IO Invalid origin được xử lý ở bản realtime tiếp theo: Nginx giữ Origin thực, websocket xác thực qua backend:8000 trong Docker. Kết quả riêng của bản realtime xem mục dưới và gps-realtime-results.json.


## Bước 4 — GPS realtime theo kiến trúc hệ thống

Phạm vi thống nhất: chưa chọn thiết bị/giao thức, dùng simulator có sẵn. Mục 10
trong luồng nghiệp vụ tổng thể mô tả thiết bị/TCP Listener tương lai; hiện tại
simulator gọi HTTP API. Không gọi đây là nghiệm thu thiết bị GPS thật.

```text
Simulator → Nginx → Frappe GPS API → Redis Queue (vị trí mới nhất + buffer)
                                     ├→ Tracking/POD → Redis Pub/Sub → Socket.IO → Nginx → Web
                                     └→ gps-flusher → MariaDB / GPS Log
Web → Frappe Tracking/POD: đăng ký xem chuyến, snapshot, lịch sử và ePOD
```

- **Tracking/POD:** `dp_tracking_and_pod/realtime.py` sở hữu đăng ký theo dõi và
  phát vị trí. API ingest cũ giữ tương thích simulator; `tracking.py` cung cấp
  snapshot theo chuyến. GPS không tự xác nhận điểm dừng hoặc hoàn tất chuyến.
- **Realtime Service:** dùng service `websocket` của Frappe, sự kiện riêng
  `dp_gps_position`; không dựng thêm server Socket.IO trùng chức năng.
- **Phân quyền:** POST `dp_dispatch.dp_tracking_and_pod.realtime.watch_trip` kiểm
  tra quyền đọc chuyến. Đăng ký hết hạn sau 90 giây; mỗi lần phát kiểm tra lại
  tài khoản enabled, role, phân công và quyền DocType. Phát vào room của từng
  user, không phát tới toàn bộ Desk hay tin tưởng mã chuyến từ client.
- **Độ mới:** chỉ bản tin mới nhất được đẩy; bản trùng không đẩy lại, bản đến muộn
  vẫn lưu lịch sử nhưng không làm vị trí nhảy lùi. Client bỏ bản khác chuyến/xe
  và bản cũ hơn vị trí đang vẽ. Sau 5 phút hoặc chuyến đã kết thúc, ghi rõ dữ liệu cũ.
- **Mất kết nối:** polling 3 giây dự phòng; reconnect đăng ký lại và lấy snapshot
  bù tin bị lỡ. Khi đang kết nối, vị trí được vẽ trực tiếp từ sự kiện, không đợi
  snapshot 30 giây. Snapshot đối soát quyền/trạng thái, không phải chu kỳ GPS chính.
- **Triển khai:** Nginx chuyển tiếp Origin thực để Frappe kiểm tra cùng nguồn.
  Service websocket gọi `http://backend:8000` để xác thực trong mạng Docker,
  mang `X-Frappe-Site-Name` cho tenant. Không tắt kiểm tra Origin. Local vẫn ở
  HTTP 8086; HTTPS/WSS 443 và firewall Ubuntu trong sơ đồ là cấu hình triển khai
  máy chủ, chưa được thay bằng tuyên bố đã triển khai trên máy Windows local.
- **Kiểm thử:** `tests/gps_realtime_socket.js` kiểm tra WebSocket thật qua Nginx,
  Origin sai, tài khoản ngoài phạm vi, simulator, mất kết nối/snapshot/reconnect.
  `tests/test_realtime_map.js` kiểm tra cập nhật marker theo sự kiện và fallback.
  `tests/gps_transport_integration.py` kiểm tra quyền, lease hết hạn/thu hồi,
  trùng/cũ và vòng đời lấy–giao–duyệt. Cấu hình token cho bài socket phải là file
  riêng ngoài Git; vô hiệu hóa tài khoản tạm sau chạy.

### Kết quả xác minh local ngày 09/11/2026

- WebSocket thật qua Nginx: simulator gửi 60 điểm, MariaDB lưu đủ 60;
  nhận trực tiếp 40 điểm, 20 điểm lúc ngắt kết nối được bù bằng snapshot.
  Kết nối lại thành công; tài khoản ngoài phạm vi nhận 0 sự kiện; Origin sai bị chặn.
- Chuyến `MAT-DT-2026-00003` hoàn tất lấy–giao, duyệt `Completed/Approved`,
  hàng trên xe về 0 kg. Tài khoản kiểm thử tạm đã bị vô hiệu hóa.
- 29 kiểm tra GPS và 24 kiểm tra vận chuyển đạt; 4 kiểm tra simulator đạt.
  Kiểm tra JavaScript marker/fallback/reconnect và hồi quy giao diện đạt.
- Báo cáo: `docs/gps-realtime-results.json`, `docs/gps-integration-results.json`.
  Chưa kiểm tra trực quan bản realtime mới trong trình duyệt do quyền điều khiển
  trình duyệt bị tắt; kiểm thử Socket.IO là kết nối mạng thật, kiểm thử marker là VM.

### Phạm vi còn lại

TCP Listener (framing/decoder/heartbeat/ACK), xác thực thiết bị và mapping thiết
bị–xe chờ giao thức cụ thể. Chưa có polyline tuyến đã duyệt từ Routes API nên
chưa kết luận lệch tuyến từ nét đứt nối điểm. AI Agent/FastAPI, OR-Tools, đề xuất
điều chỉnh/chờ phê duyệt, Mobile App riêng và Zalo/SMS vẫn là các bước tiếp theo.
Không để nhánh nhận GPS chờ AI hay tự thay đổi kế hoạch được duyệt.
