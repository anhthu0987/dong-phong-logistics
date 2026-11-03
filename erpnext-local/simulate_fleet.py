#!/usr/bin/env python3
"""Simulate several vehicles reporting GPS for N seconds (stdlib only).

Usage (WSL, from erpnext-local):
  ADMIN_PASSWORD=admin python3 simulate_fleet.py
  python3 simulate_fleet.py --duration 60 --interval 3 --password admin
  python3 simulate_fleet.py --vehicles DP-VEHICLE-01 DP-VEHICLE-02

Auth: logs in with --user/--password (default Administrator; dispatchers/System Managers
are allowed by gps.log_location). For an API key instead: --api-key KEY:SECRET
"""
import argparse, json, math, os, random, time, urllib.parse, urllib.request
from datetime import datetime
from http.cookiejar import CookieJar

p = argparse.ArgumentParser()
p.add_argument("--url", default="http://127.0.0.1:8085")
p.add_argument("--site", default="logistics.localhost")
p.add_argument("--user", default="Administrator")
p.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD", "admin"))
p.add_argument("--api-key", default=None, help="KEY:SECRET (skips login)")
p.add_argument("--vehicles", nargs="+",
               default=["DP-VEHICLE-01", "DP-VEHICLE-02", "DP-VEHICLE-03",
                        "51C-123.45", "51C-234.56", "51C-345.67"])
p.add_argument("--duration", type=int, default=60)
p.add_argument("--interval", type=float, default=3.0)
p.add_argument("--lat", type=float, default=16.0544)    # Da Nang
p.add_argument("--lng", type=float, default=108.2022)
a = p.parse_args()

opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
HDR = {"Host": a.site}
if a.api_key:
    HDR["Authorization"] = "token " + a.api_key


def call(method, data):
    req = urllib.request.Request(
        f"{a.url}/api/method/{method}",
        data=urllib.parse.urlencode(data).encode(), headers=HDR, method="POST")
    try:
        with opener.open(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode()[:300]}


if not a.api_key:
    r = call("login", {"usr": a.user, "pwd": a.password})
    if "error" in r:
        raise SystemExit(f"Login failed: {r}")
    print("Logged in as", a.user)

# each vehicle: own circle (centre offset, radius, speed, phase) + small jitter
cars = []
for i, v in enumerate(a.vehicles):
    cars.append(dict(
        id=v,
        clat=a.lat + random.uniform(-0.03, 0.03),
        clng=a.lng + random.uniform(-0.03, 0.03),
        rad=random.uniform(0.004, 0.012),
        speed=random.uniform(0.03, 0.08),           # rad/sec (~300m per 3s tick)
        phase=random.uniform(0, 2 * math.pi),
    ))

run = int(time.time())
steps = int(a.duration / a.interval)
sent = ok = 0
print(f"{len(cars)} vehicles, {steps} ticks, every {a.interval}s -> ~{steps * len(cars)} points")

t0 = time.time()
for i in range(steps):
    tick_start = time.time()
    for c in cars:
        ang = c["phase"] + c["speed"] * (i * a.interval)
        lat = c["clat"] + c["rad"] * math.sin(ang) + random.uniform(-2e-5, 2e-5)
        lng = c["clng"] + c["rad"] * math.cos(ang) + random.uniform(-2e-5, 2e-5)
        r = call("dp_dispatch.dp_dispatch.api.gps.log_location", {
            "vehicle": c["id"],
            "latitude": f"{lat:.9f}", "longitude": f"{lng:.9f}",
            "recorded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            "source_event_id": f"sim-{run}-{c['id']}-{i}",
            "source_type": "Simulated",
        })
        sent += 1
        msg = r.get("message", {})
        if isinstance(msg, dict) and msg.get("status") in ("success", "ignored"):
            ok += 1
        else:
            print(f"  ! {c['id']} tick {i}: {str(r)[:200]}")
    print(f"tick {i + 1}/{steps}  ok={ok}/{sent}  t={time.time() - t0:4.1f}s", end="\r")
    time.sleep(max(0.0, a.interval - (time.time() - tick_start)))

print(f"\nDone: {ok}/{sent} accepted.")