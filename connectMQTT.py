import time
import sys
import paho.mqtt.client as mqtt
import json
from datetime import datetime
import socketio

# ============================
# 1. LOAD FLASK + DATABASE
# ============================
from app import create_app, db
from app.models.user_model import Users
from app.models.sensor_model import DataReadings, SensorConfig
from app.models.alert_model import AlertEvent # <--- Import Model Cảnh báo

app = create_app()
app.app_context().push()

print("✅ Flask app & DB context loaded")

# ============================
# 2. CẤU HÌNH
# ============================
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_KEEPALIVE = 60
WEB_SERVER_URL = "http://127.0.0.1:1404" 

# ============================
# 3. KẾT NỐI SOCKETIO VỚI WEB SERVER
# ============================
sio = socketio.Client(logger=False, engineio_logger=False)

def connect_socketio():
    try:
        if not sio.connected:
            sio.connect(WEB_SERVER_URL, transports=['websocket', 'polling'], wait_timeout=10)
            print(f"✅ [SocketIO] Đã kết nối tới Web Server: {WEB_SERVER_URL}")
    except Exception as e:
        # In lỗi gọn hơn
        # print(f"⚠️ [SocketIO] Chưa kết nối được Web Server ({WEB_SERVER_URL}). Lỗi: {e}")
        pass

# Kết nối lần đầu
connect_socketio()

# ============================
# 4. LOAD USER TOPICS & CONFIGS
# ============================
def load_user_topics():
    try:
        users = Users.query.filter(Users.sub_topic.isnot(None)).all()
        topic_map = {}
        for user in users:
            if not user.sub_topic or user.sensor_count <= 0: continue

            # Lấy cấu hình chi tiết để check Min/Max
            configs = SensorConfig.query.filter_by(user_id=user.id_user).all()
            config_map = {c.sensor_index: c for c in configs}

            topic_map[user.sub_topic] = {
                "user_id": user.id_user,
                "username": user.username,
                "sensor_count": user.sensor_count,
                "configs": config_map
            }
            print(f"👤 User {user.username} | Topic: {user.sub_topic} | Sensors: {user.sensor_count}")
        return topic_map
    except Exception as e:
        print(f"❌ Lỗi DB: {e}")
        return {}

TOPIC_USER_MAP = load_user_topics()

# ============================
# 5. MQTT CALLBACKS
# ============================
def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print("✅ [MQTT] Kết nối thành công tới Broker")
        global TOPIC_USER_MAP
        TOPIC_USER_MAP = load_user_topics() 
        if TOPIC_USER_MAP:
            for topic in TOPIC_USER_MAP.keys():
                client.subscribe(topic)
                print(f"📡 Subscribed: {topic}")
    else:
        print(f"❌ MQTT connect failed: {reason_code}")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload_raw = msg.payload
        hex_string = payload_raw.hex().upper()

        if topic not in TOPIC_USER_MAP: return

        user_info = TOPIC_USER_MAP[topic]
        user_id = user_info["user_id"]
        sensor_count = user_info["sensor_count"]
        configs = user_info["configs"]

        if not hex_string.startswith("0103"): return

        try:
            byte_count = int(hex_string[4:6], 16)
        except: return

        if byte_count < sensor_count * 2: return

        print("MSG ..........")
        
        data_start_idx = 6
        readings_list = []
        current_time = datetime.now()

        for i in range(sensor_count):
            segment = hex_string[data_start_idx + i*4 : data_start_idx + (i+1)*4]
            if len(segment) < 4: break
            
            raw_val = int(segment, 16)
            real_val = raw_val / 10.0 
            sensor_idx = i + 1
            
            # Lấy tên cảm biến
            config = configs.get(sensor_idx)
            sensor_name = config.name if config else f"Sensor {sensor_idx}"
            
            # In log chi tiết
            print(f" {user_info['username']}|{topic} | {sensor_name} | {real_val}")

            # 1. Lưu DataReadings (Lịch sử)
            new_reading = DataReadings(
                user_id=user_id,
                sensor_index=sensor_idx,
                value=real_val,
                timestamp=current_time
            )
            db.session.add(new_reading)
            
            # 2. Kiểm tra Cảnh báo & Lưu AlertEvent
            if config:
                alert_msg = None
                if config.min_val is not None and real_val < config.min_val:
                    alert_msg = f"Thấp hơn Min ({config.min_val})"
                elif config.max_val is not None and real_val > config.max_val:
                    alert_msg = f"Cao hơn Max ({config.max_val})"
                
                if alert_msg:
                    print(f"   ⚠️ ALERT: {sensor_name} - {alert_msg}")
                    
                    # Lưu vào DB
                    new_alert = AlertEvent(
                        user_id=user_id,
                        sensor_index=sensor_idx,
                        value=real_val,
                        created_at=datetime.utcnow(),
                        sent=False # Chưa gửi email
                    )
                    db.session.add(new_alert)
                    
                    # Gửi socket alert ngay lập tức (Real-time Alert)
                    if not sio.connected: connect_socketio()
                    if sio.connected:
                        sio.emit('new_alert', {
                            'user_id': user_id, 
                            'sensor_index': sensor_idx, 
                            'value': real_val, 
                            'msg': alert_msg,
                            'timestamp': current_time.strftime('%H:%M:%S'), 
                            'sent': False
                        })

            # Chuẩn bị dữ liệu gửi realtime
            readings_list.append({
                'index': sensor_idx,
                'value': real_val
            })

        db.session.commit()
        print(f"💾 Đã lưu {len(readings_list)} giá trị.")
        print("______________________________________")

        # 3. Gửi SocketIO Update (Dữ liệu thường)
        if not sio.connected: connect_socketio()
            
        if sio.connected:
            socket_payload = {
                'user_id': user_id,
                'topic': topic,
                'device_id': topic, 
                'time': current_time.strftime('%d/%m/%Y %H:%M:%S'),
                'data': readings_list,
                'raw_hex': hex_string
            }
            sio.emit('sensor_data_update', socket_payload)
        
        # print("Nghỉ 5 giây\n")
        # time.sleep(5)
        

    except Exception as e:
        db.session.rollback()
        print(f"❌ Lỗi xử lý: {e}")
    

# ============================
# 6. MAIN LOOP
# ============================
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

print("\n🚀 MQTT COLLECTOR RUNNING...")
while True:
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n🛑 Stopped.")
        sys.exit(0)
    except Exception as e:
        print(f"⚠️ Mất kết nối: {e}. Thử lại sau 5s...")
        time.sleep(5)