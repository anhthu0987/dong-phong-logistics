param([ValidateSet('start','stop','status','backup','install','build')][string]$Action='start')
$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
$project='logistics-erpnext-v16'
$site='logistics-v16.localhost'
$envFile='.env-v16'
$composeArgs=@('compose','--project-name',$project,'--env-file',$envFile,'-f','frappe_docker/compose.yaml','-f','frappe_docker/overrides/compose.mariadb.yaml','-f','frappe_docker/overrides/compose.redis.yaml','-f','local-v16.yaml')
function Run-Compose { & docker @composeArgs @args; if($LASTEXITCODE -ne 0){throw 'Docker Compose failed. Check Docker Desktop and the output above.'} }
switch($Action){
 'build' {
   if(!(Test-Path 'frappe_docker/images/layered/Containerfile')){throw 'Clone the pinned frappe_docker revision first; see README.md.'}
   & docker build --build-arg FRAPPE_BRANCH=version-16 --secret id=apps_json,src=apps-v16.json --tag logistics-erpnext:v16 --file frappe_docker/images/layered/Containerfile frappe_docker
   if($LASTEXITCODE -ne 0){throw 'ERPNext v16 base image build failed.'}
   & docker build --tag logistics-erpnext:dispatch-v16 --file dispatch-app/Dockerfile.v16 dispatch-app
   if($LASTEXITCODE -ne 0){throw 'Dispatch v16 image build failed.'}
 }
 'start' { Run-Compose up -d; Write-Host 'ERPNext v16: http://localhost:8086' }
 'stop' { Run-Compose stop }
 'status' { Run-Compose ps }
 'backup' {
   Run-Compose exec -T backend bench --site $site backup --with-files
   New-Item -ItemType Directory -Force backups-v16 | Out-Null
   Run-Compose cp "backend:/home/frappe/frappe-bench/sites/$site/private/backups/." ./backups-v16/
 }
 'install' {
   if(!(Test-Path $envFile)){throw 'Copy .env-v16.example to .env-v16 and set unique passwords first.'}
   $cfg=@{}; Get-Content $envFile | ForEach-Object { if($_ -match '^([^#=]+)=(.*)$'){$cfg[$matches[1]]=$matches[2]} }
   foreach($key in @('DB_PASSWORD','ADMIN_PASSWORD')){if(!$cfg[$key] -or $cfg[$key] -match '^REPLACE_'){throw "Set $key in .env-v16 before installation."}}
   Run-Compose exec -T -e "SETUP_DB_PASSWORD=$($cfg['DB_PASSWORD'])" -e "SETUP_ADMIN_PASSWORD=$($cfg['ADMIN_PASSWORD'])" backend bash -c 'bench new-site logistics-v16.localhost --mariadb-user-host-login-scope="%" --db-root-password "$SETUP_DB_PASSWORD" --admin-password "$SETUP_ADMIN_PASSWORD" --install-app erpnext'
   if($LASTEXITCODE -ne 0){throw 'Site creation failed. Do not rerun against an existing site; inspect the output.'}
   Run-Compose exec -T backend bench --site $site install-app hrms
   if($LASTEXITCODE -ne 0){throw 'HRMS installation failed.'}
   Run-Compose exec -T backend bench --site $site enable-scheduler
   Write-Host 'Fresh v16 site installed. Run Deploy-v16.ps1 to install dp_dispatch.'
 }
}
