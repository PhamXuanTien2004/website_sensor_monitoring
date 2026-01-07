# File: app/models/alert_model.py
from app import db
from datetime import datetime

class AlertEvent(db.Model):
    __tablename__ = "alert_events"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, nullable=False)
    sensor_index = db.Column(db.Integer, nullable=False)

    value = db.Column(db.Float, nullable=False)

    # Thời điểm tạo bản ghi cảnh báo
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow
    )

    # Trạng thái đã gửi cảnh báo (Email/Telegram/SMS...) hay chưa
    sent = db.Column(
        db.Boolean, default=False
    )
    
    # Thời điểm của dữ liệu cảm biến (nếu khác với created_at)
    timestamp = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f"<Alert u={self.user_id} s={self.sensor_index} v={self.value}>"