import time
import requests
import argparse
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_URL = "http://127.0.0.1:8000"
ENDPOINT = "/api/method/dp_dispatch.dp_dispatch.api.gps.log_location"

VEHICLE = "51C-123.45"
DELIVERY_TRIP = "MAT-DT-2026-00001"
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

def run_simulation(config):
    api_key = os.environ.get('DP_GPS_API_KEY') or config.get('api_key')
    api_secret = os.environ.get('DP_GPS_API_SECRET') or config.get('api_secret')
    if not api_key or not api_secret:
        raise ValueError('Thiếu api_key/api_secret trong cấu hình riêng hoặc biến môi trường.')
    base_url = (os.environ.get('DP_GPS_BASE_URL') or config.get('base_url', BASE_URL)).rstrip('/')
    vehicle = config.get('vehicle', VEHICLE)
    delivery_trip = config.get('delivery_trip', DELIVERY_TRIP)
    interval = float(config.get('interval_seconds', INTERVAL_SECONDS))
    if not 0 <= interval <= 3600:
        raise ValueError('interval_seconds phải nằm trong khoảng 0–3600.')
    zone = ZoneInfo(config.get('time_zone', 'Asia/Ho_Chi_Minh'))
    run_id = uuid.uuid4().hex
    print("=" * 60)
    print("BẮT ĐẦU CHƯƠNG TRÌNH GIẢ LẬP GPS")
    print(f"Xe: {vehicle} | Chuyến: {delivery_trip} | Run ID: {run_id}")
    print(f"Tần suất: {interval}s/bản tin | Tổng số điểm: {len(SIMULATED_ROUTE)}")
    print("=" * 60)

    url = f"{base_url}{ENDPOINT}"
    headers = {
        "Authorization": f"token {api_key}:{api_secret}"
    }
    if config.get('site'):
        headers['Host'] = config['site']

    for idx, (lat, lng) in enumerate(SIMULATED_ROUTE):
        source_event_id = f"{run_id}-point-{idx+1:03d}"
        recorded_at = datetime.now(zone).strftime("%Y-%m-%d %H:%M:%S")

        payload = {
            "vehicle": vehicle,
            "delivery_trip": delivery_trip,
            "recorded_at": recorded_at,
            "latitude": lat,
            "longitude": lng,
            "source_event_id": source_event_id,
            "source_type": "Simulated"
        }

        print(f"[{idx+1}/{len(SIMULATED_ROUTE)}] Gửi tọa độ ({lat}, {lng}) lúc {recorded_at}")
        
        try:
            res = requests.post(url, data=payload, headers=headers, timeout=15, allow_redirects=False)
        except requests.RequestException:
            raise RuntimeError('Không kết nối được máy chủ; dừng mô phỏng.') from None
        if res.status_code != 200:
            raise RuntimeError(f'API trả HTTP {res.status_code}; kiểm tra tài khoản, quyền và cấu hình.')
        result = res.json().get('message', {})
        if result.get('status') not in ('success', 'ignored'):
            raise RuntimeError('Máy chủ chưa xác nhận bản tin; dừng mô phỏng.')
        print(f"   Success: {result['status']}")

        if idx < len(SIMULATED_ROUTE) - 1:
            time.sleep(interval)

    print("HOÀN THÀNH TOÀN BỘ TUYẾN ĐƯỜNG GIẢ LẬP!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Gửi tọa độ GPS giả lập bằng tài khoản API riêng.')
    parser.add_argument('--config', type=Path, default=Path(__file__).with_name('gps_config.local.json'))
    args = parser.parse_args()
    try:
        run_simulation(json.loads(args.config.read_text(encoding='utf-8-sig')))
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f'Lỗi: {exc}\n')
