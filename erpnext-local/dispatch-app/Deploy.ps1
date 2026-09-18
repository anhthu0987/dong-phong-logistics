$ErrorActionPreference='Stop'
& docker build -t logistics-erpnext:dispatch-v1 $PSScriptRoot
if($LASTEXITCODE -ne 0){throw 'Dispatch image build failed'}
& (Join-Path $PSScriptRoot '../Quan-ly.ps1') start
& docker exec logistics-erpnext-backend-1 bench --site logistics.localhost install-app dp_dispatch
if($LASTEXITCODE -ne 0){throw 'Dispatch app install failed'}
& docker exec logistics-erpnext-backend-1 bench --site logistics.localhost migrate
if($LASTEXITCODE -ne 0){throw 'Dispatch migration failed'}
& docker restart logistics-erpnext-backend-1 logistics-erpnext-queue-short-1 logistics-erpnext-queue-long-1 logistics-erpnext-scheduler-1
if($LASTEXITCODE -ne 0){throw 'Service restart failed'}
