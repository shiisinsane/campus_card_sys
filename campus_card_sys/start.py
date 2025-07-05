#!/usr/bin/env python3
# start.py - 启动脚本

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def check_dependencies():
    """检查依赖是否安装"""
    try:
        import flask
        import flask_sqlalchemy
        import requests
        print("✓ 基础依赖检查通过")

        # 检查waitress
        try:
            import waitress
            print("✓ Waitress 生产服务器可用")
        except ImportError:
            print("⚠ Waitress 未安装，将使用Flask开发服务器")
            print("  建议安装: pip install waitress")

        return True
    except ImportError as e:
        print(f"✗ 缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        return False

def init_database():
    """初始化数据库"""
    try:
        from init_data import init_test_data
        print("正在初始化数据库...")
        init_test_data()
        print("✓ 数据库初始化完成")
        return True
    except Exception as e:
        print(f"✗ 数据库初始化失败: {e}")
        return False

def start_backend():
    """启动后端服务"""
    try:
        print("正在启动后端服务...")
        # 在新的进程中启动Flask应用，不重定向输出以避免缓冲区问题
        process = subprocess.Popen([sys.executable, 'app.py'])

        # 等待服务启动
        time.sleep(5)  # 增加等待时间

        # 检查进程是否还在运行
        if process.poll() is None:
            print("✓ 后端服务启动成功 (http://localhost:5000)")
            return process
        else:
            print(f"✗ 后端服务启动失败，进程已退出")
            return None
    except Exception as e:
        print(f"✗ 启动后端服务时出错: {e}")
        return None

def open_frontend():
    """打开前端页面"""
    try:
        frontend_path = Path(__file__).parent / "index.html"
        frontend_url = f"file:///{frontend_path.absolute().as_posix()}"
        print(f"正在打开前端页面: {frontend_url}")
        webbrowser.open(frontend_url)
        print("✓ 前端页面已打开")
        return True
    except Exception as e:
        print(f"✗ 打开前端页面失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 50)
    print("校园卡管理系统启动器")
    print("=" * 50)
    
    # 检查依赖
    if not check_dependencies():
        return
    
    # 初始化数据库
    if not init_database():
        return
    
    # 启动后端
    backend_process = start_backend()
    if not backend_process:
        return
    
    # 打开前端
    open_frontend()
    
    print("\n" + "=" * 50)
    print("系统启动完成！")
    print("后端服务: http://localhost:5000")
    print("前端页面已在浏览器中打开")
    print("\n测试账号:")
    print("- 学号: 2021001, 姓名: 张三, 密码: 123456")
    print("- 学号: 2021002, 姓名: 李四, 密码: 123456")
    print("- 学号: 2021003, 姓名: 王五, 密码: 123456")
    print("\n按 Ctrl+C 停止服务")
    print("=" * 50)
    
    try:
        # 等待用户中断
        backend_process.wait()
    except KeyboardInterrupt:
        print("\n正在停止服务...")
        backend_process.terminate()
        backend_process.wait()
        print("服务已停止")

if __name__ == "__main__":
    main()
