"""Run on gps-review.localhost only; all fixture writes are rolled back.

From the bench sites directory:
../env/bin/python ../apps/dp_dispatch/tests/gps_permissions_integration.py
"""
import json
import uuid
from unittest.mock import patch

import frappe
from dp_dispatch.dp_dispatch.api import gps


def run():
    frappe.init(site="gps-review.localhost", sites_path="/home/frappe/frappe-bench/sites")
    frappe.connect()
    frappe.set_user("Administrator")
    assert frappe.local.site == "gps-review.localhost"
    tag = "GPS-PERM-" + uuid.uuid4().hex[:10]
    users = []
    checks = []

    def passed(name, condition=True):
        assert condition, name
        checks.append(name)

    def denied(name, action, error=frappe.PermissionError):
        try:
            action()
        except error:
            passed(name)
        else:
            raise AssertionError(name + ": action was accepted")

    def raw(doctype, name, **fields):
        # Minimal fixtures bypass unrelated ERP workflow validations.
        frappe.get_doc(dict(doctype=doctype, name=name, **fields)).db_insert()
        return name

    def send(vehicle, trip=None):
        event = tag + "-" + uuid.uuid4().hex
        frappe.local.form_dict = frappe._dict(
            vehicle=vehicle, delivery_trip=trip, recorded_at="2020-01-01 01:00:00",
            latitude=10.8, longitude=106.6, source_event_id=event, source_type="Simulated",
        )
        result = gps.log_location()
        assert result["status"] == "success"
        return event

    try:
        # Production methods explicitly commit; suppress only those commits so
        # this independent process can roll back every write, including failures.
        with patch.object(frappe.db, "commit", lambda: None):
            drivers = []
            for suffix in ("A", "B", "UNLINKED"):
                email = (tag + "-" + suffix).lower() + "@example.invalid"
                raw("User", email, email=email, first_name=suffix, enabled=1, user_type="System User")
                users.append(email)
                if suffix != "UNLINKED":
                    emp = raw("Employee", tag + "-EMP-" + suffix, user_id=email)
                    drivers.append(raw("Driver", tag + "-DRIVER-" + suffix, full_name=suffix, employee=emp))
            vehicle = raw("Vehicle", tag + "-VEHICLE", license_plate=tag + "-VEHICLE")
            other_vehicle = raw("Vehicle", tag + "-OTHER-VEHICLE", license_plate=tag + "-OTHER-VEHICLE")
            owned = raw("Delivery Trip", tag + "-A", driver=drivers[0], vehicle=vehicle, docstatus=1, status="Scheduled")
            foreign = raw("Delivery Trip", tag + "-B", driver=drivers[1], vehicle=vehicle, docstatus=1, status="Scheduled")
            cancelled = raw("Delivery Trip", tag + "-C", driver=drivers[0], vehicle=vehicle, docstatus=2, status="Cancelled")
            status_cancelled = raw("Delivery Trip", tag + "-D", driver=drivers[0], vehicle=vehicle, docstatus=0, status="Cancelled")
            stops = []
            for trip in (owned, foreign, cancelled, status_cancelled):
                stops.append(raw("Delivery Stop", trip + "-STOP", parent=trip, parenttype="Delivery Trip", parentfield="delivery_stops", visited=0))
            event_a = send(vehicle, owned)
            event_b = send(vehicle, foreign)
            event_unlinked = send(vehicle)
            passed("Dispatcher can read both trips", len(gps.get_gps_history(vehicle=vehicle)) == 3)

            frappe.set_user(users[0])
            passed("Real User -> Employee -> Driver mapping", gps._get_current_driver() == drivers[0])
            history = gps.get_gps_history(vehicle=vehicle)
            passed("Vehicle history excludes other driver and unassigned points", [p.source_event_id for p in history] == [event_a])
            passed("Own trip history remains readable", len(gps.get_gps_history(delivery_trip=owned)) == 1)
            denied("Explicit other trip history denied", lambda: gps.get_gps_history(delivery_trip=foreign))
            denied("Other trip write on shared vehicle denied", lambda: send(vehicle, foreign))
            denied("Driver write without trip denied", lambda: send(vehicle))
            denied("Wrong vehicle for own trip denied", lambda: send(other_vehicle, owned), frappe.ValidationError)
            send(vehicle, owned)
            passed("Own trip GPS write succeeds")
            denied("Other drivers stop denied", lambda: gps.complete_delivery_stop(stops[1]))
            denied("Cancelled docstatus stop denied", lambda: gps.complete_delivery_stop(stops[2]), frappe.ValidationError)
            denied("Cancelled status stop denied", lambda: gps.complete_delivery_stop(stops[3]), frappe.ValidationError)
            passed("Cancelled stop remains unvisited", frappe.db.get_value("Delivery Stop", stops[2], "visited") == 0)
            passed("Cancelled trip status preserved", frappe.db.get_value("Delivery Trip", cancelled, "status") == "Cancelled")
            passed("Valid own stop still completes", gps.complete_delivery_stop(stops[0])["trip_completed"])

            frappe.set_user(users[1])
            passed("Second driver sees only own history", [p.source_event_id for p in gps.get_gps_history(vehicle=vehicle)] == [event_b])
            frappe.set_user(users[2])
            denied("Unlinked user read denied", lambda: gps.get_gps_history(vehicle=vehicle))
            denied("Unlinked user write denied", lambda: send(vehicle, owned))
            frappe.set_user("Guest")
            denied("Guest read denied", lambda: gps.get_gps_history(vehicle=vehicle))
            denied("Guest write denied", lambda: send(vehicle, owned))
    finally:
        frappe.set_user("Administrator")
        frappe.db.rollback()
        for user in users:
            frappe.clear_cache(user=user)
        frappe.destroy()
    return dict(passed=len(checks), checks=checks, fixture_changes_rolled_back=True)


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
