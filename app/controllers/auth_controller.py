# File: app/controllers/auth_controller.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
# Import Model Users
try:
    from app.models.user_model import Users
except ImportError:
    from app.models import User as Users

from app.forms import LoginForm

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Controller (C) cho trang đăng nhập.
    """
    # 1. Xử lý nếu đã đăng nhập từ trước
    if current_user.is_authenticated:
        # Nếu là Admin -> Vào Dashboard
        if current_user.is_admin():
            return redirect(url_for('user.dashboard'))
        # Nếu là User -> Vào trang Theo dõi
        return redirect(url_for('user.follow_data', user_id=int(current_user.get_id())))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(username=form.username.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash('Đăng nhập thành công!', 'success')
            
            # Kiểm tra xem có trang đích (next) không
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            
            # === PHÂN LUỒNG CHUYỂN HƯỚNG ===
            if user.is_admin():
                # Admin -> Dashboard
                return redirect(url_for('user.dashboard'))
            else:
                # User -> Monitor
                return redirect(url_for('user.follow_data', user_id=user.id_user))
            
        else:
            flash('Đăng nhập thất bại. Vui lòng kiểm tra lại tên đăng nhập và mật khẩu.', 'danger')
            
    return render_template('auth/login.html', title='Đăng nhập', form=form)

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('Bạn đã đăng xuất.', 'info')
    return redirect(url_for('auth.login'))