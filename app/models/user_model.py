# File: app/models/user_model.py
from app import db, login_manager, bcrypt
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))

class Users(db.Model, UserMixin):
    __tablename__ = 'users' 
    
    id_user = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    
    # Các trường thông tin thêm
    phone_number = db.Column(db.String(15), nullable=True)
    sub_topic = db.Column(db.String(200), nullable=True)
    
    # === HAI CỘT QUAN TRỌNG CẦN CÓ ===
    sensor_count = db.Column(db.Integer, nullable=False, default=0)
    sensor_names_str = db.Column(db.String(500), nullable=True)
    # =================================

    # Quan hệ với bảng cấu hình cảm biến
    sensor_configs = db.relationship('SensorConfig', backref='owner', lazy=True, cascade="all, delete-orphan")
    readings = db.relationship('DataReadings', backref='user', lazy=True)

    def get_id(self):
        return str(self.id_user)

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'
    
    def get_sensor_names(self):
        if not self.sensor_names_str:
            return []
        return [s.strip() for s in self.sensor_names_str.split(',')]