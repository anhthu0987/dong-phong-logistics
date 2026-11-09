# HƯỚNG DẪN CHẠY VÀ DANH SÁCH TÀI KHOẢN ĐÔNG PHONG LOGISTICS

---

## 🌐 LINK TRUY CẬP CÔNG KHAI (Tailscale Funnel - Cố định vĩnh viễn)

👉 **Đường dẫn Web**: **[https://admin-pc.taild66954.ts.net/](https://admin-pc.taild66954.ts.net/)**
- Có chứng chỉ bảo mật **HTTPS** chính thức.
- **Cố định 100% vĩnh viễn**, không bao giờ bị đổi dù tắt máy hay khởi động lại.
- Dùng được từ **mọi thiết bị** (điện thoại 4G/5G, máy tính ngoài quán cafe, thầy cô/bạn cùng nhóm mở từ xa).

---

## 1. Thông tin đăng nhập hệ thống

- **Đường dẫn nội bộ**: [http://localhost:8086](http://localhost:8086)
- **Đường dẫn Internet**: [https://admin-pc.taild66954.ts.net/](https://admin-pc.taild66954.ts.net/)
- **Tài khoản**:
  - **Username**: `Administrator`
  - **Mật khẩu**: `admin`
- **Phiên bản hệ thống**:
  - Frappe: `16.55.2`
  - ERPNext: `16.54.0`
  - HRMS: `16.53.1`
  - App điều phối: `dp_dispatch` (với 6 phân hệ module nghiệp vụ: DP Sales, DP Transport Orders, DP Transport Planning, DP Tracking and POD, DP Fleet Operations, DP Accounts)
- **Công ty**: Công ty Phân phối Đông Phong (Tiền tệ: VND)

---

## 2. Cách bật / tắt hệ thống

- **Bật hệ thống**: Nhấp đúp vào **`Chay-Logistics-v16.cmd`** (tự khởi động Docker và tự mở trình duyệt).
- **Tắt hệ thống**: Nhấp đúp vào **`Dung-Logistics-v16.cmd`**.

*(Bản v15 cũ ở cổng 8085 có thể bật bằng `Chay-Logistics.cmd` nếu cần)*

---

## 3. Các trang nghiệp vụ chính trên v16

- **Bàn làm việc DP Dispatch**: [https://admin-pc.taild66954.ts.net/app/dp-dispatch](https://admin-pc.taild66954.ts.net/app/dp-dispatch)
- **Đơn vận chuyển (Delivery Order)**: [https://admin-pc.taild66954.ts.net/app/delivery-order](https://admin-pc.taild66954.ts.net/app/delivery-order)
- **Kế hoạch vận chuyển tối ưu (Transport Plan)**: [https://admin-pc.taild66954.ts.net/app/transport-plan](https://admin-pc.taild66954.ts.net/app/transport-plan)
- **Chuyến vận chuyển (Delivery Trip)**: [https://admin-pc.taild66954.ts.net/app/delivery-trip](https://admin-pc.taild66954.ts.net/app/delivery-trip)
- **Kế hoạch bảo dưỡng xe (Fleet Maintenance Plan)**: [https://admin-pc.taild66954.ts.net/app/fleet-maintenance-plan](https://admin-pc.taild66954.ts.net/app/fleet-maintenance-plan)
- **Nhật ký & Chi phí xe (Vehicle Log)**: [https://admin-pc.taild66954.ts.net/app/vehicle-log](https://admin-pc.taild66954.ts.net/app/vehicle-log)
- **Xác nhận giao hàng (Delivery Confirmation)**: [https://admin-pc.taild66954.ts.net/app/delivery-confirmation](https://admin-pc.taild66954.ts.net/app/delivery-confirmation)
- **Bản đồ giám sát đội xe (Fleet Map)**: [https://admin-pc.taild66954.ts.net/app/fleet-map](https://admin-pc.taild66954.ts.net/app/fleet-map)
- **Lịch trình GPS tài xế (Driver GPS)**: [https://admin-pc.taild66954.ts.net/app/driver-gps](https://admin-pc.taild66954.ts.net/app/driver-gps)
- **Nhật ký tọa độ GPS (GPS Log)**: [https://admin-pc.taild66954.ts.net/app/gps-log](https://admin-pc.taild66954.ts.net/app/gps-log)
- **Hóa đơn bán hàng / Cước vận chuyển (Sales Invoice)**: [https://admin-pc.taild66954.ts.net/app/sales-invoice](https://admin-pc.taild66954.ts.net/app/sales-invoice)
- **Báo cáo đối soát vận tải (Transport Reconciliation)**: [https://admin-pc.taild66954.ts.net/app/query-report/Transport%20Reconciliation](https://admin-pc.taild66954.ts.net/app/query-report/Transport%20Reconciliation)


---

## 4. Tài khoản tài xế và cách tự kiểm thử

- **Họ tên:** Trần Quang Minh
- **Tài khoản:** `minh.tran@dongphong.example`
- **Mật khẩu:** `Dp!hjQAieGfO9ENNLUgiiK`
- **Vai trò:** DP Driver (không có quyền duyệt hoàn tất).
- **Đăng nhập:** https://admin-pc.taild66954.ts.net/login
- **Local:** http://localhost:8086/login
- Đã xác minh đăng nhập bằng mật khẩu qua HTTP và kiểm tra phiên trả về đúng tài khoản. Chưa coi đây là kiểm thử toàn bộ giao diện trình duyệt.

### Dùng hai phiên đăng nhập riêng

Mở quản trị viên ở cửa sổ thường và tài xế ở cửa sổ ẩn danh hoặc trình duyệt khác. Không dùng hai tab cùng phiên để đăng nhập hai tài khoản: cookie đăng nhập được dùng chung.

### Chuyến đã hoàn tất để đối chiếu

`MAT-DT-2026-00001` đã Completed/Approved; đơn `DP-DO-2026-00001`, phiếu lấy `DP-DC-2026-00001`, phiếu giao `DP-DC-2026-00002`. Tài xế chỉ xem lại, không thể bắt đầu lại hoặc sửa kết quả. Không dùng chuyến này để thử các nút thực hiện mới.

### Tự chạy một chuyến mới

1. **Admin:** tạo báo giá mới cho khách, Submit, đánh dấu khách đã đồng ý; tạo đơn vận chuyển mới từ báo giá. Một báo giá không tạo hai đơn đang hiệu lực.
2. **Admin:** điền địa chỉ, số lượng, kg mỗi đơn vị, khung giờ lấy/giao bao phủ thời gian bạn thử; Submit đơn. Có thể dùng lại khách Bao bì Nam Phước và mặt hàng VC-BAO-BI-CARTON.
3. **Admin:** tạo Delivery Trip; chọn xe `51D-728.46`, tài xế **Trần Quang Minh** (`HR-DRI-2026-00001`), giờ xuất phát/kết thúc, số km đầu. Dùng **Thêm đơn lấy–giao**, chọn đơn mới; chỉnh giờ đến từng điểm trong khung giờ và cách nhau đủ thời gian phục vụ. Submit để chuyến ở Scheduled.
4. **Tài xế:** mở danh sách Delivery Trip, chọn chuyến mới được phân, nhấn **Bắt đầu chuyến**.
5. **Tài xế:** dùng nút **Ghi nhận giao/hoàn hàng**, chọn điểm Pickup. Nhập thời điểm thực tế, người bàn giao, lượng đã lấy bằng lượng phân và còn chờ = 0; lưu rồi Submit. Hàng trên xe phải tăng.
6. **Tài xế:** làm tương tự ở điểm Delivery. Nhập lượng đã giao, còn chờ = 0, cước đã thu đúng cước đơn và phương thức thu; Submit. Nếu giao đủ, hàng trên xe về 0. Khi thử thao tác ngoài khung giờ, cần ghi lý do ở ghi chú.
7. **Tài xế:** trở lại chuyến, tải lại và nhấn **Gửi yêu cầu kết thúc chuyến**. Tài xế không có nút tự duyệt.
8. **Admin:** tải lại chuyến, nhấn **Duyệt hoàn tất chuyến**. Kiểm tra Completed/Approved và hàng trên xe = 0.

Lưu Draft là bước trung gian của form trước Submit; kết quả cuối cần là chứng từ đã Submit và chuyến Completed. Đừng bỏ dở ở Draft khi nghiệm thu.

### Khi không thấy chuyến hoặc nút

- Kiểm tra đúng tài khoản, Driver của chuyến là Trần Quang Minh và chuyến đã Submit.
- Chỉ Scheduled mới bắt đầu được; In Transit mới xác nhận lấy/giao; phải lấy trước giao.
- Sau mỗi thao tác tải lại form để cập nhật trạng thái.
- Chọn giờ hiện tại của site, không nhập xác nhận tương lai; lượng còn chờ/hàng trên xe khác 0 sẽ chặn hoàn tất.
- Nếu giao thiếu và cần trả: phải có điểm Return trong kế hoạch để xác nhận trả người gửi. Chưa hỗ trợ thêm điểm vào chuyến đã Submit.
- Tên tài khoản có đuôi .example là định danh đăng nhập; không phải hộp thư để nhận email khôi phục. Admin có thể đặt lại mật khẩu.

File này chứa thông tin đăng nhập, chỉ lưu nội bộ; không đưa vào Git hay gửi kèm báo cáo.
