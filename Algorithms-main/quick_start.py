"""简洁的启动脚本 - 启动服务器并打开浏览器"""

import os
import subprocess
import sys
import time
import webbrowser

# 项目根目录
ROOT = r"D:\算法导论小组作业\Algorithms-main"

def main():
    print("南开大学智能排课系统 - 启动中...")
    print("=" * 50)

    # 切换到项目根目录
    os.chdir(ROOT)

    # 启动后端API
    print("[1] 启动后端API (端口 8000)...")
    api_process = subprocess.Popen(
        [sys.executable, "-m", "src.api.server"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    # 等待API启动
    time.sleep(2)

    # 启动教师端前端
    print("[2] 启动教师端 (端口 8080)...")
    teacher_process = subprocess.Popen(
        [sys.executable, "-m", "http.server", "8080"],
        cwd=os.path.join(ROOT, "web", "teacher"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    # 启动学生端前端
    print("[3] 启动学生端 (端口 8081)...")
    student_process = subprocess.Popen(
        [sys.executable, "-m", "http.server", "8081"],
        cwd=os.path.join(ROOT, "web", "student"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    # 等待所有服务启动
    time.sleep(2)

    print("")
    print("=" * 50)
    print("所有服务已启动!")
    print("=" * 50)
    print("")
    print("访问地址:")
    print("  教师端: http://localhost:8080")
    print("  学生端: http://localhost:8081")
    print("  API健康检查: http://localhost:8000/health")
    print("")

    # 打开浏览器
    print("正在打开浏览器...")
    webbrowser.open("http://localhost:8080")
    time.sleep(1)
    webbrowser.open("http://localhost:8081")

    print("")
    print("按 Ctrl+C 停止所有服务")
    print("")

    # 监控进程
    try:
        while True:
            time.sleep(1)
            # 检查进程状态
            if api_process.poll() is not None:
                print("API服务器已停止!")
                break
    except KeyboardInterrupt:
        print("\n正在停止服务...")
        api_process.terminate()
        teacher_process.terminate()
        student_process.terminate()
        print("所有服务已停止")

if __name__ == "__main__":
    main()
