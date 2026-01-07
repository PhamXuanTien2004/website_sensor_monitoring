# File: config.py
import os

# Lấy đường dẫn tuyệt đối của thư mục chứa file này
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """
    Lớp cấu hình cơ sở cho ứng dụng.
    """
    # Khóa bí mật rất quan trọng để bảo vệ session và form
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'ban-can-thay-doi-khoa-bi-mat-nay'
    
    # Cấu hình database, sử dụng SQLite cho đơn giản
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    
    # Tắt tính năng theo dõi sửa đổi của SQLAlchemy để tiết kiệm tài nguyên
    SQLALCHEMY_TRACK_MODIFICATIONS = False

