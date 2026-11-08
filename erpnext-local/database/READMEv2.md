# init
cd erpnext-local/database

docker cp install.py logistics-erpnext-backend-1:/tmp/install.py
docker cp reset_seed.py logistics-erpnext-backend-1:/tmp/reset_seed.py
docker cp run_install.sh logistics-erpnext-backend-1:/tmp/run_dp_install.sh

docker exec logistics-erpnext-backend-1 bash /tmp/run_dp_install.sh

docker cp logistics-erpnext-backend-1:/tmp/dong-phong-schema/ .


# sim
1. docker cp /home/gnoah/frappe_docker/dong-phong-logistics/erpnext-local/dispatch-app/dp_dispatch/dp_dispatch/simulator.py logistics-erpnext-backend-1:/tmp/simulator.py
2. docker exec -it logistics-erpnext-backend-1 python3 /tmp/simulator.py


# build host -> docker
docker cp erpnext-local/dispatch-app/dp_dispatch/dp_dispatch/page/fleet_map/fleet_map.js \
  logistics-erpnext-backend-1:/home/frappe/frappe-bench/apps/dp_dispatch/dp_dispatch/dp_dispatch/page/fleet_map/fleet_map.js

docker exec logistics-erpnext-backend-1 bench --site logistics.localhost clear-cache
docker exec logistics-erpnext-backend-1 bench build --app dp_dispatch
docker restart logistics-erpnext-backend-1