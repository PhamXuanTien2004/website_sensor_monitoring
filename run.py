# File: run.py
import socket
from app import app, socketio

def get_ip_address():
    """Lấy địa chỉ IP nội bộ của máy tính"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Kết nối giả đến một IP public để xác định IP nội bộ
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

if __name__ == "__main__":
    # Lấy IP máy tính
    host_ip = get_ip_address()
    port = 1404

    print("\n" + "="*50)
    print(f"🚀 SERVER ĐANG KHỞI ĐỘNG...")
    print(f" * Running on http://{host_ip}:{port}")
    print("="*50 + "\n")

    # allow_unsafe_werkzeug=True để tránh lỗi trên môi trường dev
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)