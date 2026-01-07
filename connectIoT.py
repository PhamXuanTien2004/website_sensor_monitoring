import socket
import sqlite3
import os
import time
from datetime import datetime
import socketio # Thư viện client

# --- CẤU HÌNH ---
HOST = "0.0.0.0"
PORT = 8899
DB_PATH = r"E:\TIEN_TT\web-python\app.db"
WEB_SERVER_URL = 'http://127.0.0.1:5000' # Địa chỉ Web Flask

# --- KHỞI TẠO SOCKETIO CLIENT ---
# logger=True để hiện log chi tiết khi debug
sio = socketio.Client(logger=False, engineio_logger=False)

def connect_to_web_server():
    """Thử kết nối đến Web Server"""
    if not sio.connected:
        try:
            # Thêm transports và wait_timeout để kết nối ổn định hơn
            sio.connect(WEB_SERVER_URL, transports=['websocket', 'polling'], wait_timeout=5)
            print(f"✅ [SIO] Đã kết nối thành công tới {WEB_SERVER_URL}")
        except Exception as e:
            # Chỉ in lỗi ngắn gọn để không làm rối màn hình
            print(f"⚠️ [SIO] Chưa kết nối được Web Server (Sẽ thử lại khi có dữ liệu)...")

# --- HÀM LƯU DATABASE & GỬI SOCKET ---
def save_to_database(ip_address, temp, hum):
    try:
        # 1. Lưu vào Database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        current_time = datetime.now()
        
        sql = "INSERT INTO sensor_data (tem, hum, time, ip_address) VALUES (?, ?, ?, ?)"
        cursor.execute(sql, (temp, hum, current_time, ip_address))
        conn.commit()
        print(f"[DB] ✅ Saved: IP={ip_address} | T={temp} | H={hum}")
        conn.close()

        # 2. Gửi tín hiệu lên Web qua SocketIO
        # Nếu chưa kết nối thì thử kết nối lại
        if not sio.connected:
            connect_to_web_server()
            
        if sio.connected:
            data_payload = {
                'ip': ip_address,
                'tem': temp,
                'hum': hum,
                'time': current_time.strftime('%d/%m/%Y %H:%M:%S') # Format đẹp cho Web
            }
            sio.emit('sensor_data_update', data_payload)
            print(f"[SIO] 📡 Đã gửi dữ liệu lên Web")

    except sqlite3.Error as e:
        print(f"[DB] ❌ Error: {e}")
    except Exception as e:
        print(f"[SIO] ❌ Lỗi gửi socket: {e}")

# --- CÁC HÀM XỬ LÝ MODBUS ---
def crc_ok(data: bytes):
    if len(data) < 4: return False
    crc_calc = 0xFFFF
    for pos in data[:-2]:
        crc_calc ^= pos
        for _ in range(8):
            if (crc_calc & 0x0001) != 0:
                crc_calc >>= 1
                crc_calc ^= 0xA001
            else:
                crc_calc >>= 1
    crc_recv = data[-2] | (data[-1] << 8)
    return crc_calc == crc_recv

def decode_modbus(data: bytes):
    if len(data) < 9: return None
    temp_raw = int.from_bytes(data[3:5], byteorder='big', signed=False)
    hum_raw = int.from_bytes(data[5:7], byteorder='big', signed=False)
    return temp_raw / 10.0, hum_raw / 10.0

# --- MAIN ---
def main():
    if not os.path.exists(DB_PATH):
        print(f"⚠️ Không tìm thấy DB tại: {DB_PATH}")
        return

    # Kết nối Web Server lần đầu
    print("--- BẮT ĐẦU COLLECTOR ---")
    connect_to_web_server()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((HOST, PORT))
    except OSError:
        print(f"❌ Cổng {PORT} đang bận. Hãy tắt chương trình cũ.")
        return

    server.listen(1)
    print(f"🚀 Collector đang lắng nghe tại {HOST}:{PORT}")

    while True:
        print("Waiting for module...")
        try:
            conn, addr = server.accept()
            client_ip = addr[0]
            print(f"🔌 Connected: {client_ip}")
            buffer = b""
            
            while True:
                chunk = conn.recv(1024)
                if not chunk: break
                buffer += chunk
                while len(buffer) >= 9:
                    if crc_ok(buffer[:9]):
                        result = decode_modbus(buffer[:9])
                        if result:
                            save_to_database(client_ip, *result)
                        buffer = buffer[9:]
                    else:
                        buffer = buffer[1:]
        except Exception as e:
            print(f"Error: {e}")
        finally:
            try: conn.close()
            except: pass

if __name__ == "__main__":
    main()