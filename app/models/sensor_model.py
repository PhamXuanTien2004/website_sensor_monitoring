# File: app/models/sensor_model.py
from app import db
from datetime import datetime

class SensorConfig(db.Model):
    __tablename__ = 'sensor_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id_user'), nullable=False)
    
    # Số thứ tự (1, 2, 3...)
    sensor_index = db.Column(db.Integer, nullable=False)
    
    # Tên hiển thị (VD: Nhiệt độ, Độ ẩm)
    name = db.Column(db.String(100), nullable=False, default="Thông số")
    
    # Đơn vị (VD: °C, %)
    unit = db.Column(db.String(20), nullable=True, default="")
    
    # Ngưỡng cảnh báo
    min_val = db.Column(db.Float, nullable=True)
    max_val = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f'<Config {self.name}>'

class DataReadings(db.Model):
    __tablename__ = 'data_readings'
    
    id_reading = db.Column(db.Integer, primary_key=True)
    
    # Liên kết dữ liệu với User
    user_id = db.Column(db.Integer, db.ForeignKey('users.id_user'), nullable=False)
    
    # Liên kết với cấu hình cảm biến (để biết giá trị này là của cảm biến nào)
    # sensor_index giúp map với cấu hình bên trên
    sensor_index = db.Column(db.Integer, nullable=False, default=1)
    
    # Giá trị đo được
    value = db.Column(db.Float, nullable=False)
    
    # Thời gian
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now)

    def __repr__(self):
        return f'<Data User:{self.user_id} | Idx:{self.sensor_index} | Val:{self.value}>'