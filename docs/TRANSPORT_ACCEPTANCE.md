# Luồng lấy–giao trên ERPNext v16

## Lưu trữ và phạm vi

Sử dụng MariaDB của stack v16. Frappe quản lý bảng `tabDelivery Order`,
`tabDelivery Stop`, `tabDelivery Trip`, `tabDelivery Confirmation` và bảng con.
Custom Field được cài qua `transport.install_schema()` trong hook install/migrate.
Không có database phụ hoặc SQL dump cần import bằng tay.

Chứng từ cũ dùng `Delivery Only` được giữ nguyên. Chuyến mới trên giao diện mặc
định dùng `Pickup and Delivery`. Mỗi đơn nằm trên một chuyến, có một điểm lấy,
một điểm giao và có thể thêm điểm trả người gửi sau giao; chưa hỗ trợ chia một
đơn qua nhiều chuyến hoặc giao nhiều lần tại cùng một điểm.

## Thao tác

1. Submit Quotation, ghi nhận khách đồng ý, dùng chức năng tạo Delivery Order.
2. Nhập người gửi/nhận, địa chỉ, khối lượng mỗi đơn vị, khung giờ lấy/giao và
   thời gian phục vụ; Submit đơn. Hai Address liên kết được tạo tự động.
3. Tạo Delivery Trip, chọn xe/tài xế, thời gian xuất phát/kết thúc. Dùng nút
   **Thêm đơn lấy–giao** để thêm hai điểm. Chỉnh thứ tự và thời gian đến dự kiến.
4. Nếu có dự kiến xử lý hàng trả, thêm điểm `Return` cùng đơn và khung giờ riêng.
5. Submit chuyến. Hệ thống kiểm tra đơn chưa bị phân trùng, thứ tự lấy trước giao,
   khung giờ, thời gian phục vụ và tải lớn nhất của từng chặng.
6. Tài xế bắt đầu chuyến, tạo Delivery Confirmation tại từng điểm theo thứ tự.
   Ở điểm Pickup nhập **Số lượng đã lấy lên xe**; điểm Delivery nhập **Số lượng
   đã giao**, **Cần trả người gửi**, thu cước; điểm Return nhập **Đã trả lại người gửi**.
7. Thời điểm thực tế ngoài khung giờ phải ghi lý do. Phiếu Submit phải xác định
   đủ kết quả (không còn lượng chờ). GPS/đến điểm không thay cho xác nhận hàng.
8. Tài xế gửi yêu cầu kết thúc. Admin duyệt sau khi đủ xác nhận, thu cước và
   không còn hàng trên xe. Trạng thái chuyến chỉ Completed sau duyệt.

Hàng cần trả ở điểm giao vẫn còn trên xe cho đến khi Submit phiếu Return.
Nếu chưa có kế hoạch trả trên chuyến đã Submit, hệ thống chặn hoàn tất;
chưa có chức năng tự điều chỉnh tuyến sau Submit. Không tự xóa hàng khỏi xe.

## Kiểm thử

`erpnext-local/dispatch-app/acceptance_transport.py` chạy Document insert/submit
và các API nghiệp vụ thật trên MariaDB, bao gồm chuyển người dùng tài xế/Admin.
Mặc định rollback toàn bộ. Các ca lỗi và nhánh trả hàng luôn rollback; khi đặt
`DP_ACCEPTANCE_COMMIT=1`, chỉ giữ kịch bản giao đủ với các chứng từ đã Submit và
chuyến Completed. Không giữ các chứng từ lỗi ở Draft.

Dữ liệu có tên nghiệp vụ tự nhiên, không gắn chữ demo trong bản ghi. Đây là dữ
liệu giả lập cho nghiệm thu, không phải giao dịch của khách hàng thật. Cước thu
ghi trên phiếu giao nhận chưa phải Payment Entry hoặc bút toán kế toán; không
tạo hóa đơn, gửi email/SMS hay giả lập ảnh/chữ ký của người thật.

Ca kiểm tra gồm báo giá được chấp thuận; liên kết đơn hai chiều; địa chỉ lấy/giao;
chặn đơn trùng; thứ tự điểm; khung giờ; thời gian phục vụ; tải theo chặng; phân đơn
trùng; quyền tài xế; xác nhận trùng; hàng thực tế; giao thiếu/hoàn trả; hủy phiếu
theo thứ tự; cước; yêu cầu và phê duyệt hoàn tất. Kết quả thực thi lưu trong
`transport-acceptance-results.json` cùng thư mục này.
