# COMMAND_README — cài đặt và vận hành

Tài liệu này gom các cấu hình và lệnh cần dùng để khởi tạo, build, chạy, backup và cập nhật ERPNext. Các lệnh chạy từ PowerShell trên Windows, tại đúng thư mục đã ghi.

## 1. Các file cấu hình và script

| File | Tác dụng |
|---|---|
| `erpnext-local/frappe_docker/compose.yaml` và `overrides/compose.mariadb.yaml`, `overrides/compose.redis.yaml` | Compose base và các overlay nguồn; `Quan-ly-v16.ps1` ghép ba file này với `local-v16.yaml`. Thư mục nguồn được clone ở commit cố định, không lưu trong Git dự án. |
| `erpnext-local/.env-v16.example` | Mẫu biến môi trường cho stack v16. Sao chép thành `.env-v16`, tự đặt `DB_PASSWORD` và `ADMIN_PASSWORD`; không commit file đã điền mật khẩu. |
| `erpnext-local/apps-v16.json` | Khai báo các app ERPNext và HRMS cần lấy từ nhánh `version-16` khi build image nền. |
| `erpnext-local/local-v16.yaml` | Override Compose cho v16: dùng image `logistics-erpnext:dispatch-v16`, ánh xạ web vào `127.0.0.1:8086` và MariaDB 11.8. |
| `erpnext-local/Quan-ly-v16.ps1` | Lệnh quản lý v16: `build`, `start`, `stop`, `status`, `backup`, `install`. `install` chỉ dành cho site mới chưa tồn tại. |
| `erpnext-local/dispatch-app/Dockerfile.v16` | Đóng app `dp_dispatch` vào image v16, cài Python package và đưa JavaScript vào thư mục assets. |
| `erpnext-local/dispatch-app/Deploy-v16.ps1` | Backup trước, build image app, start stack, cài app nếu cần, chạy migration và restart các service. Dùng để cập nhật app trên site v16. |
| `erpnext-local/.env.example`, `apps.json`, `local.yaml`, `Quan-ly.ps1` | Cấu hình và lệnh của stack v15 cũ. Không dùng lẫn với stack v16. |
| `erpnext-local/dispatch-app/Dockerfile`, `Deploy.ps1` | Đường build/deploy v15 cũ; script deploy này không có bước backup tự động. |
| `erpnext-local/database/Install-Database.ps1` | Bộ cài dữ liệu mô phỏng cũ cho v15. Không chạy trên `logistics-v16.localhost`. |

## 2. Yêu cầu máy

- Windows, PowerShell và Docker Desktop chạy Linux containers.
- Clone repository; trong `erpnext-local`, lấy đúng mã `frappe_docker`:

```powershell
git clone https://github.com/frappe/frappe_docker.git
git -C frappe_docker checkout 61d35da827ebc04d01b64c9e78385597ccebc9d8
```

  Nếu đã có thư mục `frappe_docker`, chỉ checkout commit trên. Không dùng thư mục nguồn khác phiên bản.
- Mở `.env-v16.example`, sao chép thành `.env-v16`, đặt mật khẩu riêng cho database và Administrator. Không gửi mật khẩu qua Git/chat.

## 3. Tạo site v16 mới lần đầu

Mở PowerShell tại thư mục `erpnext-local`:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
Copy-Item .env-v16.example .env-v16
# Mở .env-v16 và thay các giá trị REPLACE_* bằng mật khẩu riêng.
.\Quan-ly-v16.ps1 build
.\Quan-ly-v16.ps1 start
.\Quan-ly-v16.ps1 install
.\dispatch-app\Deploy-v16.ps1
```

`install` tạo site `logistics-v16.localhost`, cài ERPNext/HRMS và bật scheduler. Chỉ chạy lệnh này cho môi trường mới. Lệnh deploy cài `dp_dispatch`, tạo/cập nhật custom fields, workspace, sidebar và client scripts qua Frappe migration. Truy cập `http://localhost:8086`.

Không chạy `database/Install-Database.ps1` trên site v16: bộ dữ liệu đó dùng container và site v15. V16 có thể cần tạo dữ liệu demo qua giao diện ERPNext.

## 4. Vận hành thường ngày trên v16

Tất cả lệnh dưới đây chạy trong `erpnext-local`:

```powershell
.\Quan-ly-v16.ps1 status
.\Quan-ly-v16.ps1 start
.\Quan-ly-v16.ps1 stop
.\Quan-ly-v16.ps1 backup
.\dispatch-app\Deploy-v16.ps1
```

- `start`: khởi động stack; web chỉ bind vào máy local cổng 8086.
- `stop`: dừng container nhưng không xóa dữ liệu.
- `status`: xem trạng thái các service.
- `backup`: dùng `bench backup --with-files`, sau đó chép backup vào `erpnext-local/backups-v16/`.
- `Deploy-v16.ps1`: tự backup trước khi build/migrate. Kiểm tra Docker Desktop và site trước khi cập nhật.

Backup không được commit. Giữ đủ dung lượng ổ đĩa trước khi backup và build image.

## 5. Stack v15 cũ

Stack này dùng `logistics-erpnext`, `.env`, `apps.json`, `local.yaml`, site `logistics.localhost` và cổng 8085. Nó được giữ để tương thích môi trường cũ; không phải mặc định cho cài đặt mới.

Stack này tham chiếu `frappe_docker` commit `a0c52135d4d41c4b8acf7adfdfc5bbcba46dd4d0` và build theo nhánh `version-15`.

Trong `erpnext-local`, các lệnh điều khiển là:

```powershell
.\Quan-ly.ps1 build
.\Quan-ly.ps1 start
.\Quan-ly.ps1 status
.\Quan-ly.ps1 stop
.\Quan-ly.ps1 backup
```

`.\Quan-ly.ps1 install` chỉ tạo site mới. Với dữ liệu mô phỏng v15, chạy `.\database\Install-Database.ps1`; với app v15 chạy `.\dispatch-app\Deploy.ps1`. Trước khi dùng trên máy khác, kiểm tra tên container/site trong script và sao lưu thủ công vì script cũ không tự backup trước migration.

## 6. Build image khác với chạy stack

1. `Quan-ly-v16.ps1 build` tạo image nền `logistics-erpnext:v16`, rồi build image app `logistics-erpnext:dispatch-v16`.
2. `Quan-ly-v16.ps1 start` chạy các container dựa trên image đã build. Lệnh này không cài app hay migrate schema.
3. `Quan-ly-v16.ps1 install` khởi tạo database/site mới; không phải lệnh cập nhật.
4. `Deploy-v16.ps1` cập nhật image app, cài app nếu thiếu, migrate metadata và restart service. Đây là lệnh deploy code app.

Thay đổi `apps-v16.json` hoặc base ERPNext cần build lại image nền. Thay đổi Python/JS của `dispatch-app` cần deploy lại app; không cần tạo lại site. Tránh `docker compose down -v`, xóa volume hoặc xóa site để xử lý lỗi thông thường vì các thao tác đó có thể xóa database.

## 7. Khi gặp lỗi

- Docker báo không kết nối được engine: mở Docker Desktop, xác nhận Linux containers đang chạy, rồi thử `status`.
- Web chưa lên ngay sau `start`/deploy: chờ các service khởi động, xem `status`, sau đó tải lại trang.
- Lỗi thiếu app hoặc custom field sau deploy: chạy `Deploy-v16.ps1` sau khi backend đã `Up`; không chạy lại `install` trên site hiện hữu.
- Trước mọi thao tác migrate hoặc đổi image, tạo backup và giữ log lỗi đầy đủ để đối chiếu.
