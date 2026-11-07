# Luồng vận hành sau duyệt demo

## Quyết định thiết kế

Luồng mặc định chuyển sang `Delivery Order` của app `dp_dispatch`, không dùng `Sales Order`, `Delivery Note`, `Stock Entry` hay Warehouse để tạo đơn giao thường. `Delivery Note` vẫn được hỗ trợ cho các chứng từ ERPNext cũ, nhưng không phải bước bắt buộc của luồng giao nhanh. Số hàng hoàn được ghi trên xác nhận giao nhận; không tự tạo nhập kho.

## Các thay đổi

- Tạo `Delivery Order` và `Delivery Order Item`: khách gửi/nhận, điện thoại, địa chỉ lấy/giao, mặt hàng hoặc mô tả kiện, số lượng, đơn vị, khối lượng mỗi đơn vị, tổng lượng theo từng đơn vị, tổng khối lượng, phí, người trả phí và trạng thái.
- Khi Submit đơn, hệ thống tự tạo Address ERPNext từ địa chỉ giao để Delivery Stop dùng được trường địa chỉ bắt buộc. Nhân viên không phải tạo kho hoặc Address thủ công cho từng đơn.
- Khi chọn xe trên Delivery Trip, tải trọng cố định từ Vehicle hiện tự hiện. Khi gắn đơn, hệ thống cộng số lượng theo đơn vị và tính tổng khối lượng từ các dòng đơn; backend tính lại và chặn nếu tải vượt tải trọng xe.
- Delivery Stop có trạng thái giao nhận. Delivery Trip hiển thị sơ đồ thẻ theo điểm, màu theo trạng thái, kèm tổng hàng cần giao, đã nhận, hoàn/trả và còn chờ.
- Tài khoản có Role `DP Driver` chỉ đọc chuyến được giao cho Driver liên kết với Employee/User; chỉ đọc các đơn nằm trên những chuyến đó. Tài xế có thể bắt đầu chuyến và lập/Submit xác nhận giao nhận cho chuyến của mình.
- Tài xế gửi yêu cầu kết thúc. Chỉ `System Manager` (Admin) mới có nút và quyền backend duyệt hoặc từ chối. Duyệt chỉ được khi mọi điểm có xác nhận đã Submit, không còn hàng chờ và đã thu đủ phí.
- Phí vận chuyển lưu trên Delivery Order; khi giao nhận, tài xế nhập số thu và phương thức. Backend chặn thu vượt phí, yêu cầu phương thức thanh toán khi có thu và lưu người/thời điểm thu.

## Thiết lập người dùng tài xế

1. Tạo tài khoản User cho tài xế.
2. Trong Employee, gán User vào đúng hồ sơ Employee.
3. Trong Driver, liên kết đúng Employee.
4. Admin gán Role `DP Driver` cho User. Có thể gọi API quản trị `dp_dispatch.permissions.assign_driver_role` sau khi đã liên kết Driver–Employee–User; hàm sẽ kiểm tra liên kết trước khi gán.
5. Điều phối viên Submit Delivery Trip với Driver đó. Tài xế đăng nhập và chỉ thấy chuyến/đơn đã được phân.

## Cách trình diễn luồng mới

1. Vehicle: điền tải trọng một lần.
2. Delivery Order: chọn Customer, nhập người gửi/nhận và địa chỉ giao gồm đường, thành phố và quốc gia; thêm mặt hàng/mô tả, số lượng, đơn vị và khối lượng mỗi đơn vị; nhập phí vận chuyển. Submit đơn.
3. Delivery Trip: chọn xe và tài xế. Thêm Delivery Stop, chọn Delivery Order; Customer và địa chỉ nhận tự điền. Kiểm tra tải trọng xe, tổng khối lượng và tổng lượng theo đơn vị; Submit chuyến.
4. Tài xế mở chuyến được giao, bấm Bắt đầu chuyến. Tại điểm giao, lập Delivery Confirmation, nhập số phân giao, thực nhận, hoàn/trả; với xác nhận cuối, số còn chờ phải bằng 0. Nếu có phí, nhập đủ phí thu và phương thức trước khi Submit.
5. Trên Trip, xem thẻ màu theo điểm giao và số liệu hàng. Tài xế bấm Gửi yêu cầu kết thúc chuyến.
6. Admin mở Trip, rà kết quả từng điểm rồi bấm Duyệt hoàn tất hoặc Từ chối và ghi lý do.

## Giới hạn có chủ ý

- Số lượng được cộng theo từng UOM, không cộng lẫn `thùng`, `kiện`, `kg` thành một con số vô nghĩa.
- Mỗi Delivery Stop có một xác nhận cuối đã Submit. Nếu đang chờ giao tiếp, giữ xác nhận Draft và cập nhật trước khi Submit; hiện chưa hỗ trợ nhiều lần giao từng phần cho cùng điểm.
- Phí hiện là dữ liệu thu tiền vận hành có người/giờ/phương thức; chưa sinh Sales Invoice, Payment Entry, sổ quỹ hoặc đối soát ngân hàng. Cần thống nhất tài khoản kế toán và luồng hóa đơn trước khi tích hợp.
- Phí người gửi trả trước chưa có luồng riêng; bản hiện tại chỉ hỗ trợ thu người nhận khi giao.
- `Returned Qty` là ghi nhận vận hành, không nhập kho. Nếu dự án sau này cần quản lý tồn hoàn, khi đó mới thêm chứng từ/luồng kho trả hàng.
- Biểu đồ màu là trạng thái theo từng điểm giao, chưa phải bản đồ GPS hay tuyến đường thực tế.

## Ý tưởng nên chốt sau

- Tách **phí vận chuyển** khỏi **COD** (tiền thu hộ giá trị hàng), vì COD có người thụ hưởng, đối soát và hoàn tiền khác phí giao.
- Chốt bảng giá theo vùng/khoảng cách, khối lượng, kích thước, phụ phí và chính sách hủy trước khi tự tính phí.
- Thêm ảnh/chữ ký bắt buộc tùy loại giao, lý do giao thất bại, thử giao lại và nhật ký thay đổi để xử lý khiếu nại.
