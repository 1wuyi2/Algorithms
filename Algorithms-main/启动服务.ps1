# 南开大学智能排课系统 - PowerShell 启动脚本
# 使用 Start-Process 启动多个独立进程

$projectRoot = "D:\算法导论小组作业\Algorithms-main"

Write-Host "========================================"
Write-Host "南开大学智能排课系统 - 启动中..."
Write-Host "========================================"
Write-Host ""

# 启动后端API服务器
Write-Host "[1/3] 启动后端API服务器 (端口 8000)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$projectRoot'; Write-Host 'API Server started'; python -m src.api.server"

# 等待
Start-Sleep -Seconds 2

# 启动教师端前端
Write-Host "[2/3] 启动教师端前端服务器 (端口 8080)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$projectRoot\web\teacher'; Write-Host 'Teacher Frontend started'; python -m http.server 8080"

# 等待
Start-Sleep -Seconds 1

# 启动学生端前端
Write-Host "[3/3] 启动学生端前端服务器 (端口 8081)..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$projectRoot\web\student'; Write-Host 'Student Frontend started'; python -m http.server 8081"

Write-Host ""
Write-Host "========================================"
Write-Host "所有服务已启动!"
Write-Host "========================================"
Write-Host ""
Write-Host "访问地址:"
Write-Host "  教师端: http://localhost:8080"
Write-Host "  学生端: http://localhost:8081"
Write-Host "  API健康检查: http://localhost:8000/health"
Write-Host ""

# 打开浏览器
Write-Host "正在打开浏览器..."
Start-Process "http://localhost:8080"
Start-Process "http://localhost:8081"

Write-Host ""
Write-Host "服务已在独立窗口中运行。"
Write-Host "按 Enter 键退出..."
Read-Host
