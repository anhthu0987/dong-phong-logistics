# Fleet GPS (Redis)

## Build

```bash
cd ~/frappe_docker/dong-phong-logistics/erpnext-local

DC="docker compose --project-name logistics-erpnext --env-file .env \
  -f frappe_docker/compose.yaml \
  -f frappe_docker/overrides/compose.mariadb.yaml \
  -f frappe_docker/overrides/compose.redis.yaml \
  -f local.yaml"

docker build -t logistics-erpnext:dispatch-v1 ./dispatch-app
$DC up -d --force-recreate backend websocket scheduler queue-short queue-long frontend gps-flusher
$DC exec backend bench --site logistics.localhost clear-cache
```

## Run simulation

```bash
python3 simulate_fleet.py --password 'YOUR_ADMIN_PASSWORD'
```

Open http://logistics.localhost:8085/app/fleet-map