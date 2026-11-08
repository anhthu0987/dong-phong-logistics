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
    sig = f"{point['latitude']},{point['longitude']}"
    evt_key = _k(f"evt:{point['source_event_id']}")
    if not r.set(evt_key, sig, nx=True, ex=EVENT_TTL):
        if r.get(evt_key) == sig:
            return "duplicate"
        frappe.throw(
            f"Conflict: source_event_id {point['source_event_id']} already used with different data",
            frappe.DuplicateEntryError,
        )

    veh, ts_s = point["vehicle"], point["recorded_at"]
    prev = r.hget(_k("latest"), veh)
    pipe = r.pipeline()
    if not prev or json.loads(prev)["recorded_at"] <= ts_s:   # ignore out-of-order for "latest"
        pipe.hset(_k("latest"), veh, json.dumps(point))
        pipe.expire(_k("latest"), LATEST_TTL)
    pipe.rpush(_k("buffer"), json.dumps(point))
    pipe.execute()
    return "queued"


# ------------------------------------------------------------------ read ---
@frappe.whitelist()
def get_live_positions():
    """Fleet map data: Vehicle meta + Redis latest (fallback to last DB value)."""
    if not frappe.has_permission("Vehicle", "read"):
        frappe.throw("Not permitted", frappe.PermissionError)

    live = {k: json.loads(v) for k, v in _r().hgetall(_k("latest")).items()}
    rows = frappe.get_all(
        "Vehicle",
        fields=["name", "custom_technical_status", "custom_gps_device_id",
                "custom_last_lat", "custom_last_lng", "custom_last_gps_time"],
        order_by="name asc", limit_page_length=500,
    )
    out = []
    for v in rows:
        p = live.get(v.name)
        if p:
            lat, lng, t, src = p["latitude"], p["longitude"], p["recorded_at"][:19], p["source_type"]
        elif v.custom_last_lat and v.custom_last_lng:
            lat, lng, t, src = v.custom_last_lat, v.custom_last_lng, str(v.custom_last_gps_time or "")[:19], "Hardware GPS"
        else:
            lat = lng = t = src = None
        out.append({
            "plate": v.name, "status": v.custom_technical_status,
            "device": v.custom_gps_device_id,
            "lat": lat, "lng": lng, "time": t, "source_type": src,
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
        frappe.db.set_value("Vehicle", veh, {
            "custom_last_lat": p["latitude"],
            "custom_last_lng": p["longitude"],
            "custom_last_gps_time": p["recorded_at"],
        }, update_modified=False)


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