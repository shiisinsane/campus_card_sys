#!/usr/bin/env python3
# run_server.py - 稳定的服务器启动脚本

import sys
import os
from pathlib import Path

def check_and_install_dependencies():
    """检查并安装依赖"""
    try:
        import flask
        import flask_sqlalchemy
        import requests
        print("✓ 基础依赖已安装")
    except ImportError as e:
        print(f"✗ 缺少基础依赖: {e}")
        print("正在安装依赖...")
        os.system("pip install flask flask-sqlalchemy requests")
    
    try:
        import waitress
        print("✓ Waitress 生产服务器已安装")
        return True
    except ImportError:
        print("正在安装 Waitress 生产服务器...")
        result = os.system("pip install waitress")
        if result == 0:
            print("✓ Waitress 安装成功")
            return True
        else:
            print("✗ Waitress 安装失败，将使用Flask开发服务器")
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

def main():
    """主函数"""
    print("=" * 60)
    print("校园卡管理系统 - 稳定版启动器")
    print("=" * 60)
    
    # 检查并安装依赖
    has_waitress = check_and_install_dependencies()
    
    # 初始化数据库
    if not init_database():
        print("数据库初始化失败，程序退出")
        return
    
    # 启动服务器
    print("\n正在启动服务器...")
    
    if has_waitress:
        print("使用 Waitress 生产服务器")
        print("服务地址: http://localhost:5000")
        print("前端页面: 请在浏览器中打开 index.html")
        print("\n按 Ctrl+C 停止服务")
        print("=" * 60)
        
        # 直接导入并启动
        from app import app
        from waitress import serve
        
        with app.app_context():
            from models import db
            db.create_all()
        
        serve(
            app,
            host='0.0.0.0',
            port=5000,
            threads=10,
            connection_limit=1000,
            cleanup_interval=30,
            channel_timeout=120
        )
    else:
        print("使用 Flask 开发服务器（不推荐长时间运行）")
        print("服务地址: http://localhost:5000")
        print("前端页面: 请在浏览器中打开 index.html")
        print("\n按 Ctrl+C 停止服务")
        print("=" * 60)
        
        from app import app
        with app.app_context():
            from models import db
            db.create_all()
        
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n服务已停止")
    except Exception as e:
        print(f"\n启动失败: {e}")
        print("请检查错误信息并重试")
