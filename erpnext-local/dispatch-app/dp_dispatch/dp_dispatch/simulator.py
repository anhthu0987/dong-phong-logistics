import time
import requests
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"
ENDPOINT = "/api/method/dp_dispatch.api.gps.log_location"

VEHICLE = "51C-123.45"
DELIVERY_TRIP = "MAT-DT-2026-00001"
RUN_ID = "sim-run-001"
INTERVAL_SECONDS = 5

SIMULATED_ROUTE = [
    (10.8670, 106.6410), (10.8685, 106.6425), (10.8701, 106.6440),
    (10.8720, 106.6462), (10.8745, 106.6490), (10.8770, 106.6521),
    (10.8800, 106.6555), (10.8835, 106.6590), (10.8870, 106.6625),
    (10.8910, 106.6660), (10.8950, 106.6700), (10.8995, 106.6740),
    (10.9040, 106.6785), (10.9085, 106.6830), (10.9130, 106.6875),
    (10.9200, 106.6920), (10.9350, 106.6800), (10.9500, 106.6700),
    (10.9650, 106.6600), (10.9804, 106.6519)
]

def run_simulation():
    print("=" * 60)
    print("BẮT ĐẦU CHƯƠNG TRÌNH GIẢ LẬP GPS")
    print(f"Xe: {VEHICLE} | Chuyến: {DELIVERY_TRIP} | Run ID: {RUN_ID}")
    print(f"Tần suất: {INTERVAL_SECONDS}s/bản tin | Tổng số điểm: {len(SIMULATED_ROUTE)}")
    print("=" * 60)

    url = f"{BASE_URL}{ENDPOINT}"
    headers = {
        "Host": "logistics.localhost"
    }

    for idx, (lat, lng) in enumerate(SIMULATED_ROUTE):
        source_event_id = f"{RUN_ID}-point-{idx+1:03d}"
        recorded_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        payload = {
            "vehicle": VEHICLE,
            "delivery_trip": DELIVERY_TRIP,
            "recorded_at": recorded_at,
            "latitude": lat,
            "longitude": lng,
            "source_event_id": source_event_id,
            "source_type": "Simulated"
        }

        print(f"[{idx+1}/{len(SIMULATED_ROUTE)}] Gửi tọa độ ({lat}, {lng}) lúc {recorded_at}")
        
        try:
            res = requests.post(url, data=payload, headers=headers, timeout=5)
            if res.status_code == 200:
                print(f"   Success: {res.json().get('message', res.json())}")
            else:
                print(f"   Error {res.status_code}: {res.text}")
        except Exception as e:
            print(f"   Connect Error: {e}")

        if idx < len(SIMULATED_ROUTE) - 1:
            time.sleep(INTERVAL_SECONDS)

    print("HOÀN THÀNH TOÀN BỘ TUYẾN ĐƯỜNG GIẢ LẬP!")

if __name__ == "__main__":
    run_simulation()
