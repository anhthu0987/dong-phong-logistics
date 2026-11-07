$ErrorActionPreference='Stop'
Set-Location (Join-Path $PSScriptRoot '..')
$site='logistics-v16.localhost'
$project='logistics-erpnext-v16'
$composeArgs=@('compose','--project-name',$project,'--env-file','.env-v16','-f','frappe_docker/compose.yaml','-f','frappe_docker/overrides/compose.mariadb.yaml','-f','frappe_docker/overrides/compose.redis.yaml','-f','local-v16.yaml')

# Preserve the existing v16 site before replacing application code or migrating.
& .\Quan-ly-v16.ps1 backup
if($LASTEXITCODE -ne 0){throw 'Backup failed; deployment stopped.'}

& docker build --tag logistics-erpnext:dispatch-v16 --file dispatch-app/Dockerfile.v16 dispatch-app
if($LASTEXITCODE -ne 0){throw 'Could not build the dp_dispatch v16 image.'}

& docker @composeArgs up -d
if($LASTEXITCODE -ne 0){throw 'Could not start the v16 stack.'}

$composeArgs=@('compose','--project-name','logistics-erpnext-v16','--env-file','.env-v16','-f','frappe_docker/compose.yaml','-f','frappe_docker/overrides/compose.mariadb.yaml','-f','frappe_docker/overrides/compose.redis.yaml','-f','local-v16.yaml')
$installedApps = & docker @composeArgs exec -T backend bench --site $site list-apps
if($LASTEXITCODE -ne 0){throw 'Could not read the installed app list.'}
if(($installedApps -join "`n") -notmatch '(?m)^\s*dp_dispatch\s*$'){
    & docker @composeArgs exec -T backend bench --site $site install-app dp_dispatch
    if($LASTEXITCODE -ne 0){throw 'dp_dispatch installation failed.'}
}
& docker @composeArgs exec -T backend bench --site $site migrate
if($LASTEXITCODE -ne 0){throw 'Frappe migration failed.'}
& docker @composeArgs restart backend websocket queue-short queue-long scheduler frontend
if($LASTEXITCODE -ne 0){throw 'Could not restart v16 services.'}
Write-Host 'dp_dispatch has been deployed to the isolated v16 site at http://localhost:8086.'
