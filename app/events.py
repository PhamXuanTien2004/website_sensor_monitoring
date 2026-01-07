# File: app/events.py
from flask_socketio import emit
from app import socketio

@socketio.on('connect')
def handle_connect():
    print('>>> Client Web đã kết nối vào SocketIO!')

@socketio.on('sensor_data_update')
def handle_sensor_update(data):
    """
    Hàm này chạy khi connectIoT.py gửi tín hiệu 'sensor_data_update' lên.
    Nhiệm vụ: Đẩy (broadcast) dữ liệu đó xuống cho tất cả trình duyệt.
    """
    print(f"⚡ [Server Nhận] Dữ liệu từ {data.get('ip')}: {data.get('tem')}°C - {data.get('hum')}%")
    
    # Gửi sự kiện 'update_monitor' xuống cho file index.html xử lý
    emit('update_monitor', data, broadcast=True)