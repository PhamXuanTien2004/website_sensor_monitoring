# File: app/decorators.py
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def admin_required(f):
    """
    Decorator (C) để giới hạn quyền truy cập chỉ cho admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Kiểm tra nếu người dùng chưa đăng nhập
        if not current_user.is_authenticated:
            flash('Vui lòng đăng nhập để truy cập trang này.', 'info')
            return redirect(url_for('auth.login'))
        # Kiểm tra nếu người dùng không phải là admin
        if not current_user.is_admin():
            flash('Bạn không có quyền truy cập trang này.', 'danger')
            return redirect(url_for('user.profile')) # Chuyển hướng về trang profile của họ
        return f(*args, **kwargs)
    return decorated_function

