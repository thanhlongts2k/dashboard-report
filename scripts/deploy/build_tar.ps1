# ==============================================================================
# Helper Script: Đóng gói sạch sẽ backend thành dashboard_be.tar.gz
# ==============================================================================
$ErrorActionPreference = "Stop"
$rootPath = (Resolve-Path "$PSScriptRoot\..\..").Path
$stagingDir = "$rootPath\scratch\deploy_be_staging"
$tarFile = "$rootPath\dashboard_be.tar.gz"

if (Test-Path $stagingDir) {
    Remove-Item -Recurse -Force $stagingDir
}
if (Test-Path $tarFile) {
    Remove-Item -Force $tarFile
}

New-Item -ItemType Directory -Path $stagingDir | Out-Null

$excludeDirs = @('.venv', '.git', '__pycache__', 'scratch', 'node_modules', '.vscode', 'staticfiles')
$excludeFiles = @('*.pyc', 'db.sqlite3', 'dashboard_report.dump', '*.log', 'dump.rdb', 'celerybeat-schedule*', 'dashboard-report.zip', '*.tar.gz', '.env')

Get-ChildItem -Path $rootPath | ForEach-Object {
    $name = $_.Name
    if ($excludeDirs -notcontains $name -and $excludeFiles -notcontains $name) {
        Copy-Item -Path $_.FullName -Destination $stagingDir -Recurse -Force
    }
}

# Dọn dẹp media: xóa các file excel cũ, giữ lại session json và cấu trúc thư mục rỗng
if (Test-Path "$stagingDir\media") {
    Get-ChildItem -Path "$stagingDir\media" -Filter "*.xlsx" -Recurse | Remove-Item -Force -ErrorAction SilentlyContinue
    if (Test-Path "$stagingDir\media\auto_imports") {
        Remove-Item -Recurse -Force "$stagingDir\media\auto_imports\*" -ErrorAction SilentlyContinue
    }
    New-Item -ItemType Directory -Path "$stagingDir\media\auto_imports\success" -Force | Out-Null
    New-Item -ItemType Directory -Path "$stagingDir\media\auto_imports\backup" -Force | Out-Null
}

Get-ChildItem -Path $stagingDir -Recurse -Include $excludeFiles | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue
Get-ChildItem -Path $stagingDir -Recurse -Directory -Filter "__pycache__" | Remove-Item -Force -Recurse -ErrorAction SilentlyContinue

# Nén tar.gz chuẩn Linux
tar -czf $tarFile -C $stagingDir .
Remove-Item -Recurse -Force $stagingDir

if (Test-Path $tarFile) {
    $sizeMB = [math]::Round(((Get-Item $tarFile).Length / 1MB), 2)
    Write-Host "[OK] Da dong goi thanh cong: $tarFile ($sizeMB MB)" -ForegroundColor Green
} else {
    Write-Error "Khong the tao file $tarFile!"
}
