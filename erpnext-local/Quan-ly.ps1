param([ValidateSet('start','stop','status','backup','install','build')][string]$Action='start')
$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
$composeArgs=@('compose','--project-name','logistics-erpnext','--env-file','.env','-f','frappe_docker/compose.yaml','-f','frappe_docker/overrides/compose.mariadb.yaml','-f','frappe_docker/overrides/compose.redis.yaml','-f','local.yaml')
function Run-Compose { & docker @composeArgs @args; if($LASTEXITCODE -ne 0){throw 'Docker command failed. Check Docker Desktop and the output above.'} }
switch($Action){
 'build' {
   foreach($scriptPath in @('frappe_docker/resources/core/main-entrypoint.sh','frappe_docker/resources/core/start.sh')) {
     $absoluteScript=(Resolve-Path $scriptPath).Path
     $scriptText=[System.IO.File]::ReadAllText($absoluteScript)
     [System.IO.File]::WriteAllText($absoluteScript,$scriptText.Replace("`r`n","`n"),[System.Text.UTF8Encoding]::new($false))
   }
   & docker build --build-arg FRAPPE_BRANCH=version-15 --secret id=apps_json,src=apps.json --tag logistics-erpnext:v15 --file frappe_docker/images/layered/Containerfile frappe_docker
   if($LASTEXITCODE -ne 0){throw 'Build failed'}
 }
 'start' { Run-Compose up -d; Write-Host 'Open http://localhost:8085' }
 'stop' { Run-Compose stop }
 'status' { Run-Compose ps }
 'backup' { Run-Compose exec -T backend bench --site logistics.localhost backup --with-files; New-Item -ItemType Directory -Force backups | Out-Null; Run-Compose cp backend:/home/frappe/frappe-bench/sites/logistics.localhost/private/backups/. ./backups/ }
 'install' {
   $cfg=@{}; Get-Content .env | ForEach-Object { if($_ -match '^([^#=]+)=(.*)$'){$cfg[$matches[1]]=$matches[2]} }
   Run-Compose exec -T -e "SETUP_DB_PASSWORD=$($cfg['DB_PASSWORD'])" -e "SETUP_ADMIN_PASSWORD=$($cfg['ADMIN_PASSWORD'])" backend bash -c 'bench new-site logistics.localhost --mariadb-user-host-login-scope="%" --db-root-password "$SETUP_DB_PASSWORD" --admin-password "$SETUP_ADMIN_PASSWORD" --install-app erpnext'
   Run-Compose exec -T backend bench --site logistics.localhost install-app hrms
   Run-Compose exec -T backend bench --site logistics.localhost enable-scheduler
 }
}
