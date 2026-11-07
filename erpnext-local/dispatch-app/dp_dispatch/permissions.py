"""Data-level scoping for driver accounts."""
import frappe

DRIVER_ROLE = "DP Driver"


def is_driver(user=None):
	user = user or frappe.session.user
	return user != "Administrator" and DRIVER_ROLE in frappe.get_roles(user) and "System Manager" not in frappe.get_roles(user)


def driver_for_user(user=None):
	user = user or frappe.session.user
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	return frappe.db.get_value("Driver", {"employee": employee}, "name") if employee else None


def trip_query(user=None):
	user = user or frappe.session.user
	if not is_driver(user):
		return ""
	driver = driver_for_user(user)
	return "1=0" if not driver else "`tabDelivery Trip`.`docstatus` = 1 AND `tabDelivery Trip`.`driver` = " + frappe.db.escape(driver)


def confirmation_query(user=None):
	condition = trip_query(user)
	return "" if not condition else "`tabDelivery Confirmation`.`delivery_trip` in (select name from `tabDelivery Trip` where " + condition + ")"


def delivery_order_query(user=None):
	user = user or frappe.session.user
	if not is_driver(user):
		return ""
	driver = driver_for_user(user)
	if not driver:
		return "1=0"
	return ("`tabDelivery Order`.`name` in (select stop.custom_delivery_order from `tabDelivery Stop` stop "
		"inner join `tabDelivery Trip` trip on trip.name=stop.parent "
		"where stop.parenttype='Delivery Trip' and trip.docstatus=1 and trip.driver=" + frappe.db.escape(driver) + ")")


def vehicle_log_query(user=None):
	user = user or frappe.session.user
	if not is_driver(user):
		return ""
	return "`tabVehicle Log`.`owner` = " + frappe.db.escape(user)


def vehicle_query(user=None):
	user = user or frappe.session.user
	if not is_driver(user):
		return ""
	driver = driver_for_user(user)
	if not driver:
		return "1=0"
	return ("`tabVehicle`.`name` in (select vehicle from `tabDelivery Trip` "
		"where driver=" + frappe.db.escape(driver) + " and docstatus=1 and vehicle is not null)")


def has_trip_permission(doc, user=None, permission_type=None):
	user = user or frappe.session.user
	if not is_driver(user):
		return None
	if permission_type not in ("read", "select", None):
		return False
	return bool(doc.docstatus == 1 and driver_for_user(user) and doc.driver == driver_for_user(user))


def has_confirmation_permission(doc, user=None, permission_type=None):
	user = user or frappe.session.user
	if not is_driver(user):
		return None
	if permission_type not in ("read", "select", "create", "write", "submit", None):
		return False
	name = getattr(doc, "name", None)
	if permission_type == "create" and (not name or not frappe.db.exists("Delivery Confirmation", name)):
		if not doc.get("delivery_trip"):
			return True
		return has_trip_permission(frappe.get_doc("Delivery Trip", doc.delivery_trip), user)
	return bool(doc.delivery_trip and has_trip_permission(frappe.get_doc("Delivery Trip", doc.delivery_trip), user))


def has_delivery_order_permission(doc, user=None, permission_type=None):
	user = user or frappe.session.user
	if not is_driver(user):
		return None
	if permission_type not in ("read", "select", None):
		return False
	driver = driver_for_user(user)
	return bool(driver and frappe.db.sql("""SELECT stop.name FROM `tabDelivery Stop` stop
		INNER JOIN `tabDelivery Trip` trip ON trip.name=stop.parent
		WHERE stop.custom_delivery_order=%s AND stop.parenttype='Delivery Trip'
		AND trip.driver=%s AND trip.docstatus=1 LIMIT 1""", (doc.name, driver)))


def has_vehicle_log_permission(doc, user=None, permission_type=None):
	user = user or frappe.session.user
	if not is_driver(user):
		return None
	if permission_type == "create":
		return True
	if doc.owner != user:
		return False
	if permission_type in ("read", "select", None):
		return True
	if permission_type == "write":
		return bool(doc.docstatus == 0 and doc.get("custom_approval_status") in ("Draft", "Needs Correction"))
	return False


def has_vehicle_permission(doc, user=None, permission_type=None):
	user = user or frappe.session.user
	if not is_driver(user):
		return None
	if permission_type not in ("read", "select", None):
		return False
	driver = driver_for_user(user)
	if not driver or not doc.name:
		return False
	return bool(frappe.db.exists("Delivery Trip", {
		"driver": driver,
		"vehicle": doc.name,
		"docstatus": 1,
	}))


def install_permissions():
	from frappe.permissions import add_permission, update_permission_property
	if not frappe.db.exists("Role", DRIVER_ROLE):
		frappe.get_doc({"doctype": "Role", "role_name": DRIVER_ROLE, "desk_access": 1}).insert(ignore_permissions=True)
	rights = {
		"Delivery Trip": ("read", "select"),
		"Delivery Order": ("read", "select"),
		"Delivery Confirmation": ("read", "select", "create", "write", "submit"),
		"Vehicle Log": ("read", "select", "create", "write"),
		"Vehicle": ("read", "select"),
	}
	for doctype, permissions in rights.items():
		if not frappe.db.exists("DocType", doctype):
			continue
		add_permission(doctype, DRIVER_ROLE, 0)
		for permission in permissions:
			update_permission_property(doctype, DRIVER_ROLE, 0, permission, 1)


@frappe.whitelist(methods=["POST"])
def assign_driver_role(user, driver):
	frappe.only_for("System Manager")
	employee = frappe.db.get_value("Driver", driver, "employee")
	if not employee or frappe.db.get_value("Employee", employee, "user_id") != user:
		frappe.throw("Liên kết Driver.employee và Employee.user_id phải trỏ cùng một tài khoản.")
	install_permissions()
	frappe.get_doc("User", user).add_roles(DRIVER_ROLE)
	frappe.clear_cache(user=user)
	return DRIVER_ROLE
