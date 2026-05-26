# 南开大学智能排课系统 - 启动脚本
# 需要以管理员权限运行

Write-Host "========================================"
Write-Host "南开大学智能排课系统 - 启动中..."
Write-Host "========================================"
Write-Host ""

# 获取脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# 启动后端API服务器
Write-Host "[1/4] 启动后端API服务器 (端口 8000)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ScriptDir'; python -m src.api.server" -WindowStyle Normal

Start-Sleep -Seconds 2

# 启动教师端前端服务器
Write-Host "[2/4] 启动教师端前端服务器 (端口 8080)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ScriptDir\web\teacher'; python -m http.server 8080" -WindowStyle Normal

Start-Sleep -Seconds 1

# 启动学生端前端服务器
Write-Host "[3/4] 启动学生端前端服务器 (端口 8081)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ScriptDir\web\student'; python -m http.server 8081" -WindowStyle Normal

Start-Sleep -Seconds 1

Write-Host ""
Write-Host "========================================"
Write-Host "所有服务已启动！"
Write-Host "========================================"
Write-Host ""
Write-Host "访问地址:"
Write-Host "  教师端: http://localhost:8080"
Write-Host "  学生端: http://localhost:8081"
Write-Host "  API健康检查: http://localhost:8000/health"
Write-Host ""

# 自动打开浏览器
Write-Host "正在打开浏览器..."
Start-Process "http://localhost:8080"
Start-Process "http://localhost:8081"

Write-Host ""
Write-Host "按 Enter 键退出此脚本（服务将继续在后台运行）..."
Read-Host
