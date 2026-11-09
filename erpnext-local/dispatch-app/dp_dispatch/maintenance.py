"""Fleet maintenance plan and acceptance rules."""
import frappe
from frappe.utils import add_days, flt, getdate, now_datetime
from dp_dispatch.permissions import driver_for_user, is_driver


def fail(code, message):
    frappe.throw(f"[{code}] {message}")


def validate_vehicle_log(doc, method=None):
    user = frappe.session.user
    driver_user = is_driver(user)
    reviewer = is_vehicle_log_reviewer(user)
    transition = doc.flags.get("dp_vehicle_log_transition")
    previous = doc.get_doc_before_save() if not doc.is_new() else None
    state = doc.get("custom_approval_status") or "Draft"

    trip = None
    if doc.get("custom_delivery_trip"):
        trip = frappe.db.get_value(
            "Delivery Trip", doc.custom_delivery_trip,
            ["docstatus", "status", "vehicle", "driver"], as_dict=True,
        )
        if not trip:
            fail("DPM_LOG_TRIP", "Chuyến được liên kết không tồn tại.")
        if driver_user:
            driver = driver_for_user(user)
            if not driver or trip.driver != driver:
                frappe.throw("Bạn chỉ được ghi chi phí cho chuyến đã phân công cho mình.", frappe.PermissionError)
            if trip.docstatus != 1 or trip.status != "In Transit":
                fail("DPM_LOG_TRIP_STATUS", "Chỉ ghi chi phí cho chuyến đang thực hiện.")
            if not doc.license_plate:
                doc.license_plate = trip.vehicle
            employee = frappe.db.get_value("Driver", driver, "employee")
            if not employee:
                fail("DPM_LOG_EMPLOYEE", "Tài xế chưa được liên kết với Employee.")
            doc.employee = employee
        if doc.license_plate != trip.vehicle:
            fail("DPM_LOG_VEHICLE", "Xe trên Vehicle Log phải trùng với xe của Delivery Trip liên kết.")
    elif driver_user:
        fail("DPM_LOG_TRIP_REQUIRED", "Tài xế phải liên kết Vehicle Log với chuyến đang thực hiện.")

    if driver_user:
        if doc.owner and doc.owner != user:
            frappe.throw("Tài xế chỉ được tạo và cập nhật nhật ký của mình.", frappe.PermissionError)
        if doc.docstatus != 0:
            frappe.throw("Tài xế không được tự Submit Vehicle Log; hãy dùng nút Gửi Admin duyệt.", frappe.PermissionError)
        if state not in ("Draft", "Needs Correction", "Pending Review"):
            frappe.throw("Tài xế không được tự đổi trạng thái duyệt.", frappe.PermissionError)
        if previous:
            old_state = previous.get("custom_approval_status") or "Draft"
            if old_state not in ("Draft", "Needs Correction") and transition != "send":
                frappe.throw("Nhật ký đã gửi duyệt không thể sửa; liên hệ Admin nếu cần bổ sung.", frappe.PermissionError)
            if state != old_state and transition != "send":
                frappe.throw("Chỉ dùng nút Gửi Admin duyệt để chuyển trạng thái.", frappe.PermissionError)
        if state == "Pending Review" and transition != "send":
            frappe.throw("Chỉ dùng nút Gửi Admin duyệt để gửi nhật ký.", frappe.PermissionError)

        expense_type = doc.get("custom_expense_type")
        if not expense_type:
            fail("DPM_LOG_EXPENSE_TYPE", "Chọn loại chi phí phát sinh.")
        if expense_type == "Fuel":
            if flt(doc.fuel_qty) <= 0 or flt(doc.price) <= 0:
                fail("DPM_LOG_FUEL", "Nhập số lít và đơn giá nhiên liệu lớn hơn 0.")
            doc.custom_expense_amount = flt(doc.fuel_qty) * flt(doc.price)
        elif flt(doc.custom_expense_amount) <= 0:
            fail("DPM_LOG_AMOUNT", "Nhập số tiền chi phí lớn hơn 0.")
        if flt(doc.odometer) < flt(doc.last_odometer):
            fail("DPM_LOG_ODOMETER", "Số km hiện tại không được nhỏ hơn số km trước đó.")

    if previous and state != (previous.get("custom_approval_status") or "Draft") and not transition:
        frappe.throw("Chỉ được đổi trạng thái Vehicle Log bằng thao tác duyệt.", frappe.PermissionError)

    if doc.get("custom_delivery_trip"):
        import math
        if doc.get("custom_expense_type") == "Fuel":
            if flt(doc.fuel_qty) <= 0 or flt(doc.price) <= 0:
                fail("DPM_LOG_FUEL", "Số lít và đơn giá nhiên liệu phải lớn hơn 0.")
            doc.custom_expense_amount = flt(doc.fuel_qty) * flt(doc.price)
        if not doc.get("custom_expense_type") or not math.isfinite(flt(doc.custom_expense_amount)) or flt(doc.custom_expense_amount) <= 0:
            fail("DPM_LOG_AMOUNT", "Chi phí chuyến cần loại chi phí và số tiền hữu hạn lớn hơn 0.")

    if method == "before_submit":
        if not reviewer or state != "Approved" or not doc.flags.get("dp_vehicle_log_approval"):
            frappe.throw("Vehicle Log phải được Admin/Fleet Manager duyệt bằng nút Duyệt chi phí trước khi Submit.", frappe.PermissionError)


def is_vehicle_log_reviewer(user=None):
    user = user or frappe.session.user
    return user == "Administrator" or bool(set(frappe.get_roles(user)) & {"System Manager", "Fleet Manager"})


@frappe.whitelist()
def get_vehicle_log_defaults(delivery_trip):
    trip = frappe.get_doc("Delivery Trip", delivery_trip)
    trip.check_permission("read")
    if is_driver():
        driver = driver_for_user()
        if not driver or trip.driver != driver:
            frappe.throw("Bạn chỉ được ghi chi phí cho chuyến đã phân công cho mình.", frappe.PermissionError)
        if trip.docstatus != 1 or trip.status != "In Transit":
            frappe.throw("Chỉ ghi chi phí cho chuyến đang thực hiện.")
        employee = frappe.db.get_value("Driver", driver, "employee")
    else:
        employee = frappe.db.get_value("Driver", trip.driver, "employee") if trip.driver else None
    return {
        "delivery_trip": trip.name,
        "license_plate": trip.vehicle,
        "employee": employee,
        "last_odometer": trip.get("custom_start_odometer") or 0,
    }


@frappe.whitelist(methods=["POST"])
def send_vehicle_log_for_review(name):
    if not is_driver():
        frappe.throw("Chỉ tài xế được gửi Vehicle Log của mình để duyệt.", frappe.PermissionError)
    doc = frappe.get_doc("Vehicle Log", name)
    doc.check_permission("write")
    if doc.owner != frappe.session.user or doc.docstatus != 0:
        frappe.throw("Bạn chỉ gửi được nhật ký nháp do mình tạo.", frappe.PermissionError)
    if (doc.get("custom_approval_status") or "Draft") not in ("Draft", "Needs Correction"):
        frappe.throw("Vehicle Log này không ở trạng thái có thể gửi duyệt.")
    doc.custom_approval_status = "Pending Review"
    doc.custom_submitted_for_review_at = now_datetime()
    doc.flags.dp_vehicle_log_transition = "send"
    doc.save()
    doc.add_comment("Info", "Tài xế gửi Vehicle Log cho Admin duyệt.")
    return doc.custom_approval_status


@frappe.whitelist(methods=["POST"])
def review_vehicle_log(name, action, note=None):
    if not is_vehicle_log_reviewer():
        frappe.throw("Chỉ Admin hoặc Fleet Manager được duyệt Vehicle Log.", frappe.PermissionError)
    doc = frappe.get_doc("Vehicle Log", name)
    if doc.docstatus != 0 or doc.get("custom_approval_status") != "Pending Review":
        frappe.throw("Chỉ duyệt Vehicle Log đang ở trạng thái Chờ duyệt.")
    if action not in ("Approve", "Return", "Reject"):
        frappe.throw("Thao tác duyệt không hợp lệ.")
    if action in ("Return", "Reject") and not (note or "").strip():
        frappe.throw("Nhập lý do để tài xế biết kết quả xử lý.")

    doc.custom_review_note = (note or "").strip() or None
    doc.custom_reviewed_by = frappe.session.user
    doc.custom_reviewed_at = now_datetime()
    doc.flags.dp_vehicle_log_transition = action.lower()
    if action == "Approve":
        doc.custom_approval_status = "Approved"
        doc.flags.dp_vehicle_log_approval = True
        doc.flags.ignore_permissions = True
        doc.submit()
        doc.add_comment("Info", "Admin/Fleet Manager đã duyệt chi phí Vehicle Log.")
    else:
        doc.custom_approval_status = "Needs Correction" if action == "Return" else "Rejected"
        doc.save(ignore_permissions=True)
        doc.add_comment("Info", ("Trả Vehicle Log để bổ sung: " if action == "Return" else "Từ chối Vehicle Log: ") + doc.custom_review_note)
    return doc.custom_approval_status


def validate_plan(doc, method=None):
    if flt(doc.interval_km) < 0 or flt(doc.interval_days) < 0:
        fail("DPM_INTERVAL", "Chu kỳ km và ngày không được âm.")
    if not flt(doc.interval_km) and not flt(doc.interval_days):
        fail("DPM_INTERVAL_REQUIRED", "Cần khai báo chu kỳ bảo trì theo km hoặc theo ngày.")
    if doc.hold_start and doc.hold_end and getdate(doc.hold_end) < getdate(doc.hold_start):
        fail("DPM_HOLD", "Ngày kết thúc giữ xe không được trước ngày bắt đầu.")
    if doc.last_service_odometer and doc.next_service_odometer and flt(doc.next_service_odometer) < flt(doc.last_service_odometer):
        fail("DPM_MILEAGE", "Mốc bảo trì kế tiếp không được nhỏ hơn mốc lần trước.")


def sync_plan_vehicle_status(doc, method=None):
    # Starting/holding a plan immediately prevents new trip submissions.
    # Completing a plan never releases a vehicle automatically; an accepted
    # maintenance record performs that transition after checking open plans.
    target = {"In Progress": "Under Maintenance", "Out of Service": "Out of Service"}.get(doc.status)
    if target and frappe.db.exists("Vehicle", doc.vehicle):
        frappe.db.set_value("Vehicle", doc.vehicle, "custom_technical_status", target)


def validate_record(doc, method=None):
    plan = frappe.get_doc("Fleet Maintenance Plan", doc.maintenance_plan)
    if doc.vehicle != plan.vehicle:
        fail("DPM_VEHICLE", "Xe trên kết quả bảo trì phải trùng với xe của kế hoạch.")
    if doc.service_item != plan.service_item:
        fail("DPM_SERVICE", "Hạng mục trên kết quả phải trùng với kế hoạch.")
    if doc.vehicle_log:
        log = frappe.get_doc("Vehicle Log", doc.vehicle_log)
        if log.license_plate != plan.vehicle:
            fail("DPM_LOG_VEHICLE", "Vehicle Log tham chiếu phải thuộc đúng xe bảo trì.")
        matching_service = any(row.service_item == plan.service_item for row in log.service_detail)
        if not matching_service:
            fail("DPM_LOG_SERVICE", "Vehicle Log tham chiếu phải có đúng hạng mục dịch vụ của kế hoạch.")
    if doc.hold_start and doc.hold_end and getdate(doc.hold_end) < getdate(doc.hold_start):
        fail("DPM_HOLD", "Ngày kết thúc giữ xe không được trước ngày bắt đầu.")
    if method == "before_submit" or doc.docstatus == 1:
        if not doc.accepted:
            fail("DPM_ACCEPT", "Chỉ Submit kết quả sau khi đã nghiệm thu.")
        if not doc.work_date or not doc.odometer:
            fail("DPM_RESULT", "Cần ngày thực hiện và số km nghiệm thu.")


def accept_record(doc, method=None):
    plan = frappe.get_doc("Fleet Maintenance Plan", doc.maintenance_plan)
    if not doc.accepted:
        return
    updates = {
        "last_service_date": doc.work_date,
        "last_service_odometer": doc.odometer,
    }
    if flt(plan.interval_km):
        updates["next_service_odometer"] = flt(doc.odometer) + flt(plan.interval_km)
    if flt(plan.interval_days):
        updates["next_service_date"] = add_days(doc.work_date, int(plan.interval_days))
    frappe.db.set_value("Fleet Maintenance Plan", plan.name, updates)

    # Release only when this plan is finished and no other active maintenance
    # plan still holds the same vehicle.
    frappe.db.set_value("Fleet Maintenance Plan", plan.name, "status", "Completed")
    open_plan = frappe.db.exists("Fleet Maintenance Plan", {
        "vehicle": plan.vehicle, "status": ["in", ["In Progress", "Out of Service"]],
        "name": ["!=", plan.name],
    })
    if not open_plan and frappe.db.get_value("Vehicle", plan.vehicle, "custom_technical_status") in ("Under Maintenance", "Out of Service"):
        frappe.db.set_value("Vehicle", plan.vehicle, "custom_technical_status", "Available")
