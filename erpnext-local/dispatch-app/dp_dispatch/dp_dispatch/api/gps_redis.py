"""Redis-backed GPS pipeline.

Vehicle/device  --gps.log_location-->  Redis (latest hash + point buffer)
Fleet map       --get_live_positions-->  reads Redis (no DB hit per poll)
Flusher (3s)    drains buffer  -->  bulk insert `GPS Log` + update Vehicle.custom_last_*

Uses the *queue* redis (persistent, not LRU-evicted like redis_cache).
"""
import json
import time

import frappe
import redis
from frappe.utils import now_datetime

FLUSH_INTERVAL = 3          # seconds
MAX_BATCH = 5000            # points per flush
LATEST_TTL = 24 * 3600      # drop stale "latest" entries after a day
LOCK_TTL = 10               # seconds, > worst-case flush time
_pool = {}


# ----------------------------------------------------------------- redis ---
def _r():
    url = frappe.conf.get("redis_queue")
    if not url:
        frappe.throw("redis_queue is not configured in common_site_config.json")
    if url not in _pool:
        _pool[url] = redis.Redis.from_url(url, decode_responses=True)
    return _pool[url]


def _k(name):
    return f"dp:{frappe.local.site}:gps:{name}"


# --------------------------------------------------------------- enqueue ---
EVENT_TTL = 3600  # duplicate-detection window (seconds)


def enqueue(point):
    """Called by gps.log_location after validation. Only touches Redis.

    point: dict(vehicle, delivery_trip, recorded_at 'YYYY-MM-DD HH:MM:SS[.ffffff]',
                latitude, longitude, source_type, source_event_id)
    Returns "queued" or "duplicate"; raises DuplicateEntryError on conflicting replay.
    """
    r = _r()
    if point.get('delivery_trip') and not r.exists(_k('trip:' + point['delivery_trip'])):
        previous = latest_for_trip(point['delivery_trip'], point['vehicle'])
        if previous:
            r.set(_k('trip:' + point['delivery_trip']), json.dumps(dict(previous), default=str), nx=True, ex=LATEST_TTL)
    sig = json.dumps(point, sort_keys=True)
    # One atomic operation: deduplication, monotonic latest positions and enqueue.
    result = r.eval("""
        local previous = redis.call('GET', KEYS[1])
        if previous then
            if previous == ARGV[1] then return 'duplicate' end
            return 'conflict'
        end
        redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[4])
        for i=3,4 do
            if KEYS[i] ~= '' then
                local old = redis.call('GET', KEYS[i])
                if not old or cjson.decode(old).recorded_at <= ARGV[2] then
                    redis.call('SET', KEYS[i], ARGV[1], 'EX', ARGV[3])
                end
            end
        end
        redis.call('RPUSH', KEYS[2], ARGV[1])
        return 'queued'
    """, 4, _k('evt:' + point['source_event_id']), _k('buffer'),
        _k('vehicle:' + point['vehicle']),
        _k('trip:' + point['delivery_trip']) if point.get('delivery_trip') else '',
        sig, point['recorded_at'], LATEST_TTL, EVENT_TTL)
    if result == 'conflict':
        frappe.throw('source_event_id đã được dùng với dữ liệu khác.', frappe.DuplicateEntryError)
    return result


# ------------------------------------------------------------------ read ---
def latest_for_trip(trip, vehicle):
    cached = _r().get(_k('trip:' + trip))
    point = json.loads(cached) if cached else None
    if point and point.get('vehicle') == vehicle:
        return point
    rows = frappe.get_all('GPS Log', filters={'delivery_trip': trip, 'vehicle': vehicle},
        fields=['vehicle', 'delivery_trip', 'latitude', 'longitude', 'recorded_at', 'source_type'],
        order_by='recorded_at desc, name desc', limit_page_length=1)
    return rows[0] if rows else None


@frappe.whitelist()
def get_live_positions(delivery_trip=None):
    """Only positions belonging to readable trips; never a vehicle's later trip."""
    from dp_dispatch.tracking import list_trips, readable_trip
    trips = [readable_trip(delivery_trip)] if delivery_trip else list_trips(active_only=1)
    out = []
    for trip in trips:
        p = latest_for_trip(trip.name, trip.vehicle)
        out.append({
            'plate': trip.vehicle, 'delivery_trip': trip.name, 'status': trip.status,
            'lat': p['latitude'] if p else None, 'lng': p['longitude'] if p else None,
            'time': str(p['recorded_at']) if p else None,
            'source_type': p['source_type'] if p else None,
        })
    return out


# ----------------------------------------------------------------- flush ---
def flush():
    """Drain Redis buffer -> DB. Safe to call concurrently (Redis lock)."""
    r = _r()
    if not r.set(_k("flush_lock"), "1", nx=True, ex=LOCK_TTL):
        return 0
    try:
        pipe = r.pipeline()                       # atomic drain
        pipe.lrange(_k("buffer"), 0, MAX_BATCH - 1)
        pipe.ltrim(_k("buffer"), MAX_BATCH, -1)
        raw = pipe.execute()[0]
        if not raw:
            return 0

        points = [json.loads(x) for x in raw]
        try:
            _write(points)
            frappe.db.commit()
        except Exception:
            frappe.db.rollback()
            r.lpush(_k("buffer"), *reversed(raw))  # put back at the head, retry next tick
            raise
        return len(points)
    finally:
        r.delete(_k("flush_lock"))


def _write(points):
    ts = now_datetime()
    fields = ["name", "owner", "creation", "modified", "modified_by", "docstatus", "idx",
              "vehicle", "delivery_trip", "recorded_at", "latitude", "longitude",
              "source_event_id", "source_type"]
    values = [
        (frappe.generate_hash(length=10), "Administrator", ts, ts, "Administrator", 0, 0,
         p["vehicle"], p["delivery_trip"], p["recorded_at"], p["latitude"], p["longitude"],
         p["source_event_id"], p["source_type"])
        for p in points
    ]
    # unique(source_event_id) -> replays/duplicates are silently skipped
    frappe.db.bulk_insert("GPS Log", fields, values, ignore_duplicates=True)

    latest = {}
    for p in points:
        if p["vehicle"] not in latest or latest[p["vehicle"]]["recorded_at"] <= p["recorded_at"]:
            latest[p["vehicle"]] = p
    for veh, p in latest.items():
        # Delayed batches cannot rewind the persisted fallback position.
        frappe.db.sql("""UPDATE `tabVehicle`
            SET custom_last_lat=%s, custom_last_lng=%s, custom_last_gps_time=%s
            WHERE name=%s AND (custom_last_gps_time IS NULL OR custom_last_gps_time <= %s)""",
            (p['latitude'], p['longitude'], p['recorded_at'], veh, p['recorded_at']))



def run_flusher():
    """Long-running loop: flush every 3s.

    bench --site <site> execute dp_dispatch.dp_dispatch.api.gps_redis.run_flusher
    """
    while True:
        started = time.monotonic()
        try:
            flush()
        except Exception:
            frappe.log_error(title="GPS flush failed")
            frappe.db.rollback()
        time.sleep(max(0.0, FLUSH_INTERVAL - (time.monotonic() - started)))


def scheduled_flush():
    """Fallback (cron, every minute) in case the flusher process is down."""
    flush()