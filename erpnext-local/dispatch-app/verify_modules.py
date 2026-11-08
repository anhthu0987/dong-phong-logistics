"""Run with bench's Python on a migrated site; no test records are committed."""
import frappe
from frappe.model.base_document import get_controller
from dp_dispatch.module_navigation import AREAS, install_workspaces, install_sidebar


def verify(site='logistics.localhost'):
    frappe.init(site=site, sites_path='/home/frappe/frappe-bench/sites')
    frappe.connect()
    frappe.set_user('Administrator')
    try:
        expected = {
            'Delivery Order': 'DP Transport Orders',
            'Delivery Order Item': 'DP Transport Orders',
            'Delivery Confirmation': 'DP Tracking and POD',
            'Delivery Confirmation Item': 'DP Tracking and POD',
            'Fleet Maintenance Plan': 'DP Fleet Operations',
            'Fleet Maintenance Record': 'DP Fleet Operations',
        }
        for dt, module in expected.items():
            assert frappe.get_meta(dt).module == module, dt
            package = module.lower().replace(' ', '_')
            assert get_controller(dt).__module__.startswith(f'dp_dispatch.{package}.'), dt
        assert frappe.db.exists('Module Def', 'DP Transport Planning')
        for dt in ('Vehicle', 'Driver', 'Delivery Trip', 'Customer', 'Sales Invoice'):
            assert not frappe.get_meta(dt).module.startswith('DP '), dt
        names = ['DP Dispatch'] + [area[0] for area in AREAS]
        for name in names:
            assert frappe.db.exists('Workspace', name), name
        def links():
            return {name: [(r.type, r.label, r.link_type, r.link_to)
                           for r in frappe.get_doc('Workspace', name).links] for name in names}
        before = links()
        install_workspaces()
        install_sidebar()
        assert links() == before, 'Workspace installation must be idempotent'
        tracking = frappe.get_doc('Workspace', 'DP Tracking and POD')
        assert any(row.link_to == 'Delivery Confirmation' for row in tracking.links)
        planning = frappe.get_doc('Workspace', 'DP Transport Planning')
        assert any(row.link_to == 'Delivery Trip' for row in planning.links)
        print('PASS: six controllers, module ownership, seven workspaces and repeatable installation')
        print('Record counts:', {dt: frappe.db.count(dt) for dt in expected})
    finally:
        frappe.db.rollback()
        frappe.destroy()


if __name__ == '__main__':
    verify()
