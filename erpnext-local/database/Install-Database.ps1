# Stop script executing on error
$ErrorActionPreference = 'Stop'

# Define source files on Host
$installFile = Join-Path $PSScriptRoot 'install.py'
$seedFile    = Join-Path $PSScriptRoot 'reset_seed.py'
$runnerFile  = Join-Path $PSScriptRoot 'run_install.sh'

# 1. Copy install.py to Container
Write-Host ">>> [1/5] Copying install.py to Docker container..." -ForegroundColor Cyan
& docker cp $installFile logistics-erpnext-backend-1:/tmp/install.py
if ($LASTEXITCODE -ne 0) { throw 'Could not copy install.py to container' }

# 2. Copy reset_seed.py to Container
Write-Host ">>> [2/5] Copying reset_seed.py to Docker container..." -ForegroundColor Cyan
& docker cp $seedFile logistics-erpnext-backend-1:/tmp/reset_seed.py
if ($LASTEXITCODE -ne 0) { throw 'Could not copy reset_seed.py to container' }

# 3. Copy runner script run_install.sh to Container
Write-Host ">>> [3/5] Copying run_install.sh to Docker container..." -ForegroundColor Cyan
& docker cp $runnerFile logistics-erpnext-backend-1:/tmp/run_dp_install.sh
if ($LASTEXITCODE -ne 0) { throw 'Could not copy runner script' }

# 4. Execute runner script inside Container
Write-Host ">>> [4/5] Running installation & seeding inside container..." -ForegroundColor Cyan
& docker exec logistics-erpnext-backend-1 bash /tmp/run_dp_install.sh
if ($LASTEXITCODE -ne 0) { throw 'Schema installation / seeding failed. Review output; do not reset the site.' }

# 5. Export generated schema/results back to Host
Write-Host ">>> [5/5] Exporting schema & results back to Host..." -ForegroundColor Cyan
& docker cp logistics-erpnext-backend-1:/tmp/dong-phong-schema/. $PSScriptRoot
if ($LASTEXITCODE -ne 0) { throw 'Schema export failed' }

Write-Host ">>> SUCCESS: Database installation and seeding completed successfully!" -ForegroundColor Green