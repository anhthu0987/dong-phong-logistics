# dp_dispatch

Custom Frappe app cho điều phối và vận hành logistics Đông Phong.

- Tài liệu triển khai, lệnh PowerShell, Compose/YAML, init/build/run/backup: [COMMAND_README](../../docs/COMMAND_README.md).
- Kiến trúc app, DocType/schema, luồng nghiệp vụ, quyền và API: [DOC_README](../../docs/DOC_README.md).
- Tài liệu thao tác demo: [THANH_VIEN_2](../../docs/THANH_VIEN_2.md) và [THAY_DOI_VAN_HANH_SAU_DEMO](../../docs/THAY_DOI_VAN_HANH_SAU_DEMO.md).

Mã app ở `dp_dispatch/`. `setup.py` khai báo custom fields và cài Client Scripts/workspace; `hooks.py` gắn backend validation và document events. Frappe quản lý schema thông qua DocType metadata và migration; không tạo schema trực tiếp bằng SQL.

Không cài `dp_dispatch` bằng `pip` vào máy host. Build/deploy trong stack Docker theo COMMAND_README; site v15 và v16 dùng cấu hình, container, database và cổng riêng.
