
from app import app
from waitress import serve

if __name__ == '__main__':
    print("正在启动 Waitress 服务器...")
    print("服务地址: http://localhost:5000")
    print("按 Ctrl+C 停止服务")
    
    serve(
        app,
        host='0.0.0.0',
        port=5000,
        threads=10,
        connection_limit=1000,
        cleanup_interval=30,
        channel_timeout=120
    )
