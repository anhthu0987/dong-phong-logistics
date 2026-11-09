# Kế hoạch → OR-Tools → phê duyệt → chuyến

## Kiến trúc
OpenStreetMap cung cấp dữ liệu đường Việt Nam (Geofabrik). OSRM v5.27.1 tự host trong Docker cung cấp Table API (thời gian/khoảng cách) và Route API (GeoJSON tuyến). OR-Tools 9.12 chạy trong FastAPI nội bộ, không cần Google API key. Không công khai cổng OSRM/optimizer. Optimizer yêu cầu token riêng, lưu trong optimizer/.env và site_config, không commit vào Git.

Luồng: Transport Plan → Redis Queue → Frappe worker → FastAPI → OSRM → OR-Tools → phương án Ready → điều phối duyệt → Delivery Trip Submit.

## Sử dụng
1. Khai báo tải trọng và loại xe trên Vehicle; loại xe yêu cầu trên Delivery Order nếu cần.
2. Kiểm tra tọa độ Address của điểm lấy và giao, bật `Đã kiểm tra tọa độ dùng lập tuyến`. Không tự đoán địa chỉ từ tên.
3. DP Transport Planning → Transport Plan → tạo kế hoạch, chọn đơn đã Submit, xe/tài xế, tọa độ xuất phát đã xác nhận, giờ xuất phát và hạn về.
4. Tính phương án. Tải lại form để xem trạng thái và kết quả. Có thể mở lại để chỉnh/tính lại; phiên bản và thay đổi được lưu bởi Version của Frappe.
5. Xem thứ tự điểm, giờ đến, tải từng chặng, tổng khoảng cách và hình dạng tuyến. Từ chối cần lý do.
6. Duyệt và phát hành. Backend khóa và kiểm tra lại nguồn lực, đơn, tọa độ, thời gian. Phương án cũ bị chặn. Các chuyến được Submit trong cùng giao dịch; duyệt lặp trả cùng danh sách chuyến.
7. Chuyến tiếp tục qua bắt đầu, GPS, lấy/giao, duyệt hoàn tất và kế toán. Bản đồ chuyến hiển thị GeoJSON OSRM đã lưu.

## Phạm vi
- Tối đa 10 đơn, 5 xe, kế hoạch 48 giờ. Tất cả đơn phải có đủ lấy/giao; không chia đơn hoặc âm thầm bỏ đơn.
- Mỗi xe trở về điểm xuất phát; lượng hàng ban đầu bằng 0. Tải trọng tính bằng gram, thời gian giây.
- Thời gian theo tốc độ đường tĩnh, không có dữ liệu giao thông trực tiếp. Profile car chuẩn chưa bảo đảm đầy đủ hạn chế riêng xe tải (chiều cao, tải cầu, giờ cấm). Điều phối phải rà soát tuyến.
- Bản đồ OSM là snapshot, không tự cập nhật. Dữ liệu: © OpenStreetMap contributors, ODbL; nguồn https://download.geofabrik.de/asia/vietnam.html.
- Tuyến thiếu/đứt hoặc OSRM lỗi thì Failed; không thay bằng khoảng cách đường chim bay.
- Chuyến cũ vẫn hoạt động. Chuyến mới không được Submit ngoài cơ chế duyệt kế hoạch.
- Chưa có trình sửa thứ tự tuyến thủ công; từ chối/mở lại sẽ tính phương án mới.

## Quản trị
`erpnext-local/Prepare-OSRM.ps1 -Download` tải và xử lý snapshot Việt Nam. Cần dung lượng đĩa và RAM đủ; chạy lại khi cập nhật bản đồ, không sửa trực tiếp dữ liệu đang phục vụ. Image xử lý và server phải cùng phiên bản.
`optimizer/.env`: OSRM_URL=http://osrm:5000 và OPTIMIZER_TOKEN là bí mật nội bộ. Không đưa file vào Git.

## Kiểm thử
- optimizer/test_solver.py: lấy trước giao, tải, loại xe, ma trận thiếu, chặng không tìm được.
- tests/planning_integration.py: dữ liệu nghiệp vụ tự nhiên, OSRM/OR-Tools thực, snapshot cũ bị chặn, duyệt lặp không trùng, Submit chuyến và bắt đầu. Mặc định rollback; DP_PLAN_QUEUE=1 tạo kế hoạch và kiểm thử hàng đợi thực.
