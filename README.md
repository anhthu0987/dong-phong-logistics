# Đông Phong Logistics

Repository cho ứng dụng Frappe `dp_dispatch` và môi trường ERPNext v16 local phục vụ điều phối giao hàng thông minh, lập kế hoạch tuyến đường (OSRM & OR-Tools), giám sát GPS thời gian thực và tích hợp kế toán vận tải.

---

## 🌐 Đường dẫn truy cập trực tiếp (Tailscale Funnel)

Hệ thống đang hoạt động và được public qua đường dẫn cố định vĩnh viễn:
👉 **[https://admin-pc.taild66954.ts.net/](https://admin-pc.taild66954.ts.net/)**
- Có chứng chỉ bảo mật HTTPS chính thức.
- Truy cập từ mọi thiết bị (máy tính, điện thoại, mạng ngoài quán cafe...).
- Local endpoint nội bộ: [http://localhost:8086](http://localhost:8086)

---

## 📚 Tài liệu bắt đầu nhanh

- **[TAI_KHOAN_VA_HUONG_DAN](TAI_KHOAN_VA_HUONG_DAN.md)**: Hướng dẫn đăng nhập, tài khoản Admin/Tài xế và các bước thực hành quy trình giao vận thực tế.
- **[MODULE_MAPPING](docs/MODULE_MAPPING.md)**: Kiến trúc 6 phân hệ cốt lõi: Tái sử dụng (Reuse), Mở rộng (Customize) và Viết mới (Build new).
- **[DOC_README](docs/DOC_README.md)**: Kiến trúc app, cấu trúc thư mục, DocType/schema, luồng nghiệp vụ, validation và API.
- **[PLANNING_OSRM](docs/PLANNING_OSRM.md)**: Hệ thống lập kế hoạch tuyến đường tự động bằng OSRM (OpenStreetMap) và Google OR-Tools.
- **[ACCOUNTING_INTEGRATION](docs/ACCOUNTING_INTEGRATION.md)**: Tích hợp kế toán vận tải, tự động tạo Sales Invoice, hạch toán Payment Entry và đối soát cước/lợi nhuận.
- **[GPS_INTEGRATION](docs/GPS_INTEGRATION.md)**: Giám sát GPS thời gian thực qua Socket.IO và bản đồ Fleet Map.
- **[COMMAND_README](docs/COMMAND_README.md)**: Tổng hợp file YAML/JSON cấu hình Docker, lệnh PowerShell, init site, build, chạy, backup và deploy.
- **[Phân công nhóm](docs/PHAN_CONG.md)**: Phạm vi ban đầu của các thành viên.
- **[Thành viên 2 – hướng dẫn vận hành](docs/THANH_VIEN_2.md)**: Hướng dẫn demo, quy trình giao hàng, duyệt chi phí và vận hành.

---

## 6 Phân hệ nghiệp vụ chính (Workspaces)

1. **DP Sales (Bán hàng & Khách hàng)**: Quản lý Customer, Address, Contact, Quotation, Item.
2. **DP Transport Orders (Đơn vận chuyển)**: Quản lý Delivery Order, Delivery Order Item.
3. **DP Transport Planning (Kế hoạch & Tuyến đường)**: Quản lý Transport Plan (tối ưu tuyến OSRM + OR-Tools), Delivery Trip, Delivery Stop.
4. **DP Tracking and POD (Theo dõi & Bàn giao)**: Quản lý Delivery Confirmation (ePOD), GPS Log, Fleet Map realtime, Lịch trình tài xế.
5. **DP Fleet Operations (Quản trị đội xe)**: Quản lý Vehicle, Driver, Fleet Maintenance Plan/Record, Vehicle Log (chi phí chuyến).
6. **DP Accounts (Kế toán & Đối soát cước)**: Quản lý Sales Invoice, Payment Entry, Báo cáo đối soát vận tải Transport Reconciliation.

---

## Các thành phần kỹ thuật

- `erpnext-local/dispatch-app`: Ứng dụng Frappe `dp_dispatch`, validation điều phối, tích hợp kế toán và giao diện desk.
- `erpnext-local/optimizer`: Dịch vụ FastAPI giải bài toán tối ưu lộ trình xe (VRP/CVRP) bằng OR-Tools kết hợp bản đồ OSRM cục bộ.
- `erpnext-local/local-v16.yaml`: Docker Compose stack hoàn chỉnh (Frontend, Backend, Scheduler, Queue Workers, Redis, MariaDB, OSRM, Optimizer).

## Cẩn trọng cấu hình riêng
Không commit `.env`, mật khẩu cá nhân, bản backup dữ liệu thật hoặc thư mục `osrm-data/` vào Git.
