param([switch]$Download)
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$data=Join-Path $PSScriptRoot 'osrm-data'
New-Item -ItemType Directory -Force $data | Out-Null
if ($Download) {
  Invoke-WebRequest 'https://download.geofabrik.de/asia/vietnam-latest.osm.pbf' -OutFile (Join-Path $data 'vietnam.osm.pbf')
}
if (!(Test-Path (Join-Path $data 'vietnam.osm.pbf'))) { throw 'Missing Vietnam OSM PBF; run with -Download first.' }
$image='ghcr.io/project-osrm/osrm-backend:v5.27.1'
docker run --rm --memory=5g --memory-swap=6g --cpus=2 -v "${data}:/data" $image osrm-extract -t 2 -p /opt/car.lua /data/vietnam.osm.pbf
if ($LASTEXITCODE -ne 0) { throw 'OSRM extract failed' }
docker run --rm --memory=5g --memory-swap=6g --cpus=2 -v "${data}:/data" $image osrm-partition -t 2 /data/vietnam.osrm
if ($LASTEXITCODE -ne 0) { throw 'OSRM partition failed' }
docker run --rm --memory=5g --memory-swap=6g --cpus=2 -v "${data}:/data" $image osrm-customize -t 2 /data/vietnam.osrm
if ($LASTEXITCODE -ne 0) { throw 'OSRM customize failed' }
Write-Host 'OSRM data ready. Restart the osrm service.'
