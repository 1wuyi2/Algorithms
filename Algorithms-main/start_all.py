"""启动脚本 - 同时启动后端API和前端服务器"""

import http.server
import json
import os
import socketserver
import sys
import threading
import time
import webbrowser
from urllib.parse import parse_qs, urlparse
import urllib.request

# 改变工作目录到项目根目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def start_api_server():
    """启动后端API服务器"""
    print("[1/3] 启动后端API服务器 (端口 8000)...")
    from src.api.server import run
    run(host="127.0.0.1", port=8000)

def start_teacher_frontend():
    """启动教师端前端服务器"""
    print("[2/3] 启动教师端前端服务器 (端口 8080)...")
    os.chdir(os.path.join(os.path.dirname(__file__), "web", "teacher"))
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("127.0.0.1", 8080), Handler) as httpd:
        httpd.serve_forever()

def start_student_frontend():
    """启动学生端前端服务器"""
    print("[3/3] 启动学生端前端服务器 (端口 8081)...")
    os.chdir(os.path.join(os.path.dirname(__file__), "web", "student"))
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("127.0.0.1", 8081), Handler) as httpd:
        httpd.serve_forever()

def wait_for_api():
    """等待API服务器启动"""
    print("等待API服务器启动...")
    for i in range(30):  # 等待最多30秒
        try:
            response = urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=1)
            if response.status == 200:
                print("API服务器已就绪!")
                return True
        except:
            pass
        time.sleep(1)
    return False

def check_frontend(port):
    """检查前端服务器是否就绪"""
    try:
        response = urllib.request.urlopen(f"http://127.0.0.1:{port}/index.html", timeout=1)
        return response.status == 200
    except:
        return False

def main():
    print("=" * 50)
    print("南开大学智能排课系统")
    print("=" * 50)
    print()

    # 启动API服务器线程
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()

    # 等待API服务器启动
    if not wait_for_api():
        print("错误: API服务器启动失败!")
        sys.exit(1)

    # 启动前端服务器线程
    teacher_thread = threading.Thread(target=start_teacher_frontend, daemon=True)
    teacher_thread.start()

    student_thread = threading.Thread(target=start_student_frontend, daemon=True)
    student_thread.start()

    time.sleep(2)

    # 检查所有服务
    print()
    print("=" * 50)
    print("所有服务已启动!")
    print("=" * 50)
    print()
    print("访问地址:")
    print("  教师端: http://localhost:8080")
    print("  学生端: http://localhost:8081")
    print("  API健康检查: http://localhost:8000/health")
    print()

    # 打开浏览器
    print("正在打开浏览器...")
    webbrowser.open("http://localhost:8080")
    time.sleep(1)
    webbrowser.open("http://localhost:8081")

    print()
    print("按 Ctrl+C 停止所有服务")
    print()

    # 保持运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止服务...")
        sys.exit(0)

if __name__ == "__main__":
    main()
