"""Authenticated, short-lived trip watches; never broadcast GPS to all Desk users."""
import time

import frappe

from dp_dispatch.permissions import driver_for_user, is_driver

EVENT = 'dp_gps_position'
WATCH_TTL = 90


def can_watch(trip, user):
    if user == 'Guest' or not frappe.db.get_value('User', user, 'enabled'):
        return False
    roles = set(frappe.get_roles(user))
    if user != 'Administrator' and not roles & {'System Manager', 'Fleet Manager', 'DP Driver'}:
        return False
    if is_driver(user) and (trip.docstatus != 1 or trip.driver != driver_for_user(user)):
        return False
    return bool(frappe.has_permission('Delivery Trip', doc=trip, user=user, ptype='read'))


@frappe.whitelist(methods=['POST'])
def watch_trip(delivery_trip):
    from dp_dispatch.tracking import readable_trip
    from dp_dispatch.dp_dispatch.api.gps_redis import _r, _k
    trip = readable_trip(delivery_trip)
    if not can_watch(trip, frappe.session.user):
        frappe.throw('Bạn không có quyền theo dõi chuyến.', frappe.PermissionError)
    key = _k('watch:' + trip.name)
    pipe = _r().pipeline()
    pipe.zremrangebyscore(key, '-inf', time.time())
    pipe.zadd(key, {frappe.session.user: time.time() + WATCH_TTL})
    pipe.expire(key, WATCH_TTL)
    pipe.execute()
    return {'event': EVENT, 'expires_in': WATCH_TTL}


def publish_position(point):
    """Recheck access on each message, including driver reassignment/revocation."""
    from dp_dispatch.dp_dispatch.api.gps_redis import _r, _k
    if not point.get('delivery_trip'):
        return
    trip = frappe.get_doc('Delivery Trip', point['delivery_trip'])
    if trip.docstatus != 1 or trip.status != 'In Transit' or trip.vehicle != point['vehicle']:
        return
    key = _k('watch:' + trip.name)
    redis = _r()
    redis.zremrangebyscore(key, '-inf', time.time())
    for user in redis.zrange(key, 0, -1):
        if not can_watch(trip, user):
            redis.zrem(key, user)
            continue
        frappe.publish_realtime(EVENT, dict(point), user=user, after_commit=True)
