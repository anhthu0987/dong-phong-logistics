# Bước 5 — tích hợp kế toán vận tải

Trạng thái ngày 09/11/2026: đã sao lưu, build, triển khai và migrate trên ERPNext v16. Nghiệm thu backend trên MariaDB đạt. Chưa kiểm thử bấm xuyên suốt bằng trình duyệt.

## Luồng
- Đơn mặc định Collect on Delivery: giữ quy tắc thu đủ khi giao.
- Đơn Credit: phải có hạn thanh toán, được hoàn tất nghiệp vụ khi còn công nợ.
- Chuyến đã được duyệt hoàn tất → Delivery Order / Kế toán / Lập hóa đơn cước.
- Hóa đơn lấy dòng dịch vụ và thuế/chiết khấu từ Quotation, kiểm tra tổng bằng shipping_fee. Không lấy hàng đang chở làm hàng xuất bán. Hiện chỉ hỗ trợ đồng tiền công ty.
- Kế toán kiểm tra và Submit Sales Invoice để ghi nhận doanh thu/phải thu.
- Delivery Confirmation / Kế toán / Hạch toán tiền thực thu → Payment Entry. Chọn đúng quỹ đang giữ tiền; tài xế thu tiền không đồng nghĩa đã nộp quỹ công ty. Chuyển quỹ bằng nghiệp vụ Internal Transfer chuẩn sau khi thực nộp.
- Tiền khách trả sau dùng Payment Entry chuẩn từ hóa đơn. Chặn thu trực tiếp nếu tiền tài xế khai thu còn chưa hạch toán.
- Vehicle Log được duyệt/Submit → Journal Entry: Nợ chi phí, Có tiền đã chi hoặc khoản phải hoàn ứng. Chưa chi thì không ghi Có quỹ. Việc trả hoàn ứng là nghiệp vụ kế toán chuẩn riêng.
- Không ghi trùng cùng Vehicle Log qua Journal Entry và Expense Claim. Không gộp chi phí nhà cung cấp/VAT đầu vào vào bút toán đơn giản; dùng quy trình mua hàng phù hợp trước khi mở rộng tích hợp.
- Nút tạo chứng từ mở Draft để kế toán rà soát; không tự động Submit hay thay đổi chứng từ có sẵn. Nghiệm thu tích hợp sẽ thực hiện Submit/cancel thật rồi rollback toàn bộ dữ liệu thử.

## Đối soát
DP Accounts → Transport Reconciliation, hoặc nút Kế toán trên Delivery Trip.
Một dòng/chuyến: cước, cước chưa xuất hóa đơn, doanh thu chưa thuế, thu/hoàn Payment Entry, công nợ ERPNext, tài xế khai thu, tiền chưa hạch toán, chi phí duyệt/đã hạch toán/chưa hạch toán và lãi gộp.
Bộ lọc ngày là ngày khởi hành, số dư là hiện tại; không phải báo cáo số dư tại ngày quá khứ.
Không cộng tiền tài xế khai thu với Payment Entry để tính doanh thu. Công nợ lấy outstanding_amount của hóa đơn. Chi phí hạch toán lấy GL Entry chưa hủy.

## Kiểm tra đã chạy
- 14 unit test kế toán đạt: công nợ/thu đủ, số tiền sai, nguồn trùng, sai quyền, sai đơn/chuyến, gỡ nguồn, hủy nguồn, chi phí và Expense Claim trùng.
- Kiểm tra cú pháp Python và JavaScript đạt.
- Frontend regression giao nhận và realtime map đạt.
- Đã chạy tests/accounting_integration.py trên ERPNext thực: đơn Credit hoàn tất với thu 200.000/600.000 VND; hóa đơn và thu tiền qua Submit; chống tạo trùng; chặn thu trực tiếp trùng; hủy/thu lại cập nhật công nợ; chi phí 100.000 VND vào GL và hủy đảo chi phí; báo cáo khớp sổ cái.
- Chạy lại acceptance_transport.py mặc định Collect on Delivery: 24 kiểm tra đạt.
- Xác nhận Report và Workspace Link có trên site, tài xế bị chặn API kế toán, asset accounting.js HTTP 200.
- Bộ nghiệm thu dùng transaction rollback; không để lại hóa đơn/thu tiền thử trong sổ thật. Chứng từ trong kiểm thử đều thực hiện Submit/cancel trước rollback.

## Lệnh triển khai / chạy lại nghiệm thu
Tại thư mục gốc dự án, PowerShell:
```powershell
$repoRoot = (Get-Location).Path
& ./erpnext-local/Quan-ly-v16.ps1 backup
Set-Location $repoRoot
if ($LASTEXITCODE -ne 0) { throw 'Backup failed' }
docker build -t logistics-erpnext:dispatch-v16 -f erpnext-local/dispatch-app/Dockerfile.v16 erpnext-local/dispatch-app
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
& ./erpnext-local/Quan-ly-v16.ps1 start
Set-Location $repoRoot
if ($LASTEXITCODE -ne 0) { throw 'Start failed' }
docker exec logistics-erpnext-v16-backend-1 bench --site logistics-v16.localhost migrate
if ($LASTEXITCODE -ne 0) { throw 'Migration failed' }
docker exec -w /home/frappe/frappe-bench/sites logistics-erpnext-v16-backend-1 /home/frappe/frappe-bench/env/bin/python /home/frappe/frappe-bench/apps/dp_dispatch/tests/accounting_integration.py
if ($LASTEXITCODE -ne 0) { throw 'Accounting acceptance failed' }
```
Sau nghiệm thu backend, kiểm tra các nút/form trên trình duyệt bằng tài khoản kế toán và tài xế. Chưa xác nhận bước giao diện này.
