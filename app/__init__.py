# File: app/__init__.py
import click
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_socketio import SocketIO
# XÓA: from flask_mqtt import Mqtt (Không cần nữa vì đã dùng connectMQTT.py riêng)
from config import Config

# Khởi tạo các extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
socketio = SocketIO()
# XÓA: mqtt = Mqtt()

login_manager.login_view = 'auth.login'
login_manager.login_message = 'Vui lòng đăng nhập để truy cập trang này.'
login_manager.login_message_category = 'info'

def create_app(config_class=Config):
    """
    Hàm factory để tạo và cấu hình ứng dụng Flask.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # --- CẤU HÌNH MQTT ĐÃ BỊ LOẠI BỎ ---
    # Vì logic MQTT đã được chuyển sang script độc lập connectMQTT.py
    # app.config['MQTT_...'] = ...
    # -----------------------------------
    
    # Khởi tạo extensions với ứng dụng
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    
    # Gắn SocketIO (QUAN TRỌNG: Đây là cổng giao tiếp với connectMQTT.py)
    socketio.init_app(app, async_mode='eventlet') 
    
    # XÓA: mqtt.init_app(app)

    # Nhập models
    with app.app_context():
        from app import models

    # Đăng ký Blueprints
    from app.controllers.auth_controller import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.controllers.user_controller import user_bp
    app.register_blueprint(user_bp) 
    
    # Import events (SocketIO) để xử lý dữ liệu realtime từ connectMQTT.py gửi sang
    with app.app_context():
        try:
            from app import events
            # XÓA: from app import mqtt_handler (Không dùng nữa)
        except ImportError:
            pass

    register_commands(app)

    return app

def register_commands(app):
    """
    Đăng ký các lệnh dòng lệnh (CLI) cho ứng dụng.
    """
    @app.cli.command("create-db")
    def create_db():
        """Tạo các bảng trong cơ sở dữ liệu."""
        with app.app_context():
            db.create_all()
        print("Đã tạo cơ sở dữ liệu!")

    @app.cli.command("create-admin")
    @click.argument("username")
    @click.argument("email")
    @click.argument("password")
    @click.argument("fullname")
    def create_admin(username, email, password, fullname):
        """Tạo một tài khoản admin ban đầu."""
        with app.app_context():
            from app.models.user_model import Users
            if Users.query.filter_by(username=username).first() or Users.query.filter_by(email=email).first():
                print(f"Người dùng '{username}' hoặc một admin khác đã tồn tại.")
                return

            admin = Users(
                username=username,
                email=email,
                fullname=fullname,
                role='admin'
            )
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            print(f"Đã tạo tài khoản admin: {username}")

app = create_app()