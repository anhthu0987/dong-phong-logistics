$ErrorActionPreference='Stop'
$schemaFile=Join-Path $PSScriptRoot 'install_schema.py'
& docker cp $schemaFile logistics-erpnext-backend-1:/tmp/install_dong_phong_schema.py
if($LASTEXITCODE -ne 0){throw 'Could not copy installer'}
$runner=Join-Path $PSScriptRoot 'run_install.sh'
& docker cp $runner logistics-erpnext-backend-1:/tmp/run_dp_install.sh
if($LASTEXITCODE -ne 0){throw 'Could not copy runner'}
& docker exec logistics-erpnext-backend-1 bash /tmp/run_dp_install.sh
if($LASTEXITCODE -ne 0){throw 'Schema installation failed. Review output; do not reset the site.'}
& docker cp logistics-erpnext-backend-1:/tmp/dong-phong-schema/. $PSScriptRoot
if($LASTEXITCODE -ne 0){throw 'Schema export failed'}
