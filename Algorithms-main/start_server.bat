@echo off
echo ========================================
echo 南开大学智能排课系统 - 启动脚本
echo ========================================
echo.

:: 启动后端API服务器
echo [1/3] 启动后端API服务器...
start "API Server" cmd /k "cd /d %~dp0 && python -m src.api.server"

:: 等待一下
timeout /t 2 /nobreak > nul

:: 启动教师端前端服务器
echo [2/3] 启动教师端前端服务器...
start "Teacher Frontend" cmd /k "cd /d %~dp0web\teacher && python -m http.server 8080"

:: 等待一下
timeout /t 1 /nobreak > nul

:: 启动学生端前端服务器
echo [3/3] 启动学生端前端服务器...
start "Student Frontend" cmd /k "cd /d %~dp0web\student && python -m http.server 8081"

:: 等待一下
timeout /t 1 /nobreak > nul

echo.
echo ========================================
echo 所有服务已启动！
echo ========================================
echo.
echo 访问地址:
echo   教师端: http://localhost:8080
echo   学生端: http://localhost:8081
echo   API健康检查: http://localhost:8000/health
echo.
echo 按任意键打开浏览器...
pause > nul

:: 打开浏览器
start http://localhost:8080
start http://localhost:8081

echo.
echo 服务已在后台运行，关闭此窗口不会停止服务。
pause
