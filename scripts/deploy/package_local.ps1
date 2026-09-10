# ==============================================================================
# SCRIPT DONG GOI BACKEND & DATABASE TAI LOCAL WINDOWS
# Du an: Dashboard Report 2026
# ==============================================================================

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " [1/3] DANG EXPORT DATABASE TU POSTGRESQL (PORT 5433)... " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

$rootPath = Resolve-Path "$PSScriptRoot\..\.."
Set-Location $rootPath

$dumpFile = "$rootPath\dashboard_report.dump"
$zipFile = "$rootPath\dashboard-report.zip"

if (Test-Path $dumpFile) {
    Remove-Item -Force $dumpFile
}
if (Test-Path $zipFile) {
    Remove-Item -Force $zipFile
}

# Doc mat khau tu .env local neu co
$dbPass = ""
if (Test-Path "$rootPath\.env") {
    $envLines = Get-Content "$rootPath\.env"
    foreach ($line in $envLines) {
        if ($line -match '^DB_PASSWORD\s*=\s*[''"]?(.*?)[''"]?\s*$') {
            $dbPass = $matches[1]
            break
        }
    }
}
if (-not $dbPass -and $env:PGPASSWORD) {
    $dbPass = $env:PGPASSWORD
}
$env:PGPASSWORD = $dbPass
& pg_dump -U postgres -h localhost -p 5433 -d reportdb -F c -b -v -f $dumpFile

if (Test-Path $dumpFile) {
    $dumpSize = [math]::Round(((Get-Item $dumpFile).Length / 1MB), 2)
    Write-Host "[OK] Da xuat Database thanh cong: $dumpFile ($dumpSize MB)" -ForegroundColor Green
} else {
    Write-Error "Khong the tao file dump!"
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " [2/3] DANG DONG GOI MA NGUON BACKEND... " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

$tempDeployDir = "$rootPath\scratch\deploy_temp"
if (Test-Path $tempDeployDir) {
    Remove-Item -Recurse -Force $tempDeployDir
}
New-Item -ItemType Directory -Path $tempDeployDir | Out-Null

$excludeDirs = @('.venv', '.git', '__pycache__', 'scratch', 'node_modules', '.vscode')
$excludeFiles = @('*.pyc', 'db.sqlite3', 'dashboard_report.dump', '*.log', 'dump.rdb', 'celerybeat-schedule*', 'dashboard-report.zip')

Get-ChildItem -Path $rootPath | ForEach-Object {
    $name = $_.Name
    if ($excludeDirs -notcontains $name -and $excludeFiles -notcontains $name) {
        Copy-Item -Path $_.FullName -Destination $tempDeployDir -Recurse -Force
    }
}

# Loai bo 700+ file Excel cu trong media/auto_imports de giam 248MB rac (DB PostgreSQL da co san du lieu)
if (Test-Path "$tempDeployDir\media\auto_imports") {
    Remove-Item -Recurse -Force "$tempDeployDir\media\auto_imports\*" -ErrorAction SilentlyContinue
}

Get-ChildItem -Path $tempDeployDir -Recurse -Include $excludeFiles | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
Get-ChildItem -Path $tempDeployDir -Recurse -Directory -Filter "__pycache__" | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue

Write-Host "Dang nen tap tin $zipFile..." -ForegroundColor DarkGray
Compress-Archive -Path "$tempDeployDir\*" -DestinationPath $zipFile -CompressionLevel Optimal
Remove-Item -Recurse -Force $tempDeployDir

$zipSize = [math]::Round(((Get-Item $zipFile).Length / 1MB), 2)
Write-Host "[OK] Da dong goi ma nguon thanh cong: $zipFile ($zipSize MB)" -ForegroundColor Green

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " [3/3] HOAN TAT! LENH UPLOAD LEN LINUX SERVER " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "Chay cac lenh sau de upload len server Linux (thay IP va user cua ban):" -ForegroundColor White
Write-Host "scp `"$dumpFile`" user@server-ip:/tmp/" -ForegroundColor Yellow
Write-Host "scp `"$zipFile`" user@server-ip:/tmp/" -ForegroundColor Yellow
Write-Host "scp `"$rootPath\scripts\deploy\server_deploy.sh`" user@server-ip:/tmp/" -ForegroundColor Yellow
Write-Host ""
Write-Host "Sau khi upload, tren server Linux chi can chay duy nhat 1 lenh:" -ForegroundColor Cyan
Write-Host "sudo bash /tmp/server_deploy.sh" -ForegroundColor Green
