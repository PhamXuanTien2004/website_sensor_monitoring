# File: app/controllers/user_controller.py
import os
import json # <--- THÊM MỚI
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.user_model import Users
from app.models.sensor_model import DataReadings, SensorConfig
from app.models.alert_model import AlertEvent
from app.forms import RegistrationForm, EditUserForm
from app.decorators import admin_required

user_bp = Blueprint('user', __name__)

@user_bp.route('/')
@user_bp.route('/profile', methods=['GET'])
@login_required
def profile():
    return render_template('users/profile.html', title='Thông tin cá nhân', user=current_user)

@user_bp.route('/admin/dashboard', methods=['GET'])
@login_required
@admin_required
def dashboard():
    page = request.args.get('page', 1, type=int)
    users_pagination = Users.query.paginate(page=page, per_page=5)
    return render_template('users/index.html', title='Quản lý người dùng', users=users_pagination)

@user_bp.route('/admin/create_user', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            # 1. Tạo User
            user = Users(
                fullname=form.fullname.data,
                email=form.email.data,
                username=form.username.data,
                phone_number=form.phone_number.data,
                sub_topic=form.sub_topic.data,
                sensor_count=form.sensor_count.data,
                sensor_names_str=form.sensor_names_str.data 
            )
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.flush() # Lấy ID user trước khi commit

            # 2. Xử lý JSON cấu hình cảm biến chi tiết
            # Lấy chuỗi JSON từ form (trường ẩn sensor_config_json)
            # Lưu ý: form.sensor_config_json là trường chúng ta thêm vào Form class
            # Nếu chưa thêm vào Form class, ta có thể lấy trực tiếp từ request.form
            config_json_str = request.form.get('sensor_config_json')
            configs = []
            
            if config_json_str:
                try:
                    configs = json.loads(config_json_str)
                    # configs sẽ là list các dict: 
                    # [{'index':1, 'name':'...', 'unit':'...', 'min':..., 'max':...}, ...]
                except json.JSONDecodeError:
                    print("Lỗi decode JSON config, sẽ dùng logic mặc định")
            
            # 3. Tạo cấu hình cảm biến (SensorConfig)
            count = form.sensor_count.data
            
            for i in range(1, count + 1):
                # Tìm config tương ứng trong JSON (nếu có)
                cfg = next((c for c in configs if c.get('index') == i), None)
                
                if cfg:
                    # Lấy dữ liệu từ JSON
                    name = cfg.get('name') or f"Thông số {i}"
                    unit = cfg.get('unit', '')
                    min_val = cfg.get('min') # Có thể là None
                    max_val = cfg.get('max') # Có thể là None
                else:
                    # Logic mặc định (nếu không có JSON hoặc JSON thiếu)
                    # Fallback về logic tách chuỗi sensor_names_str cũ
                    name = f"Thông số {i}"
                    unit = ""
                    min_val = None
                    max_val = None
                    
                    # Logic cũ: lấy tên từ chuỗi phân cách phẩy (backup)
                    sensor_names_old = []
                    if form.sensor_names_str.data:
                         sensor_names_old = [x.strip() for x in form.sensor_names_str.data.split(',')]
                    
                    if i <= len(sensor_names_old) and sensor_names_old[i-1]:
                        name = sensor_names_old[i-1]

                new_config = SensorConfig(
                    user_id=user.id_user,
                    sensor_index=i,
                    name=name,
                    unit=unit,
                    min_val=min_val,
                    max_val=max_val
                )
                db.session.add(new_config)

            db.session.commit()
            flash(f'Đã tạo tài khoản {form.username.data} và cấu hình {count} cảm biến!', 'success')
            return redirect(url_for('user.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi tạo tài khoản: {str(e)}', 'danger')
            print(f"Error create_user: {e}") # Log lỗi ra console để debug
            
    return render_template('users/create.html', title='Tạo người dùng mới', form=form)

@user_bp.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = Users.query.get_or_404(user_id)
    
    # Khởi tạo form
    form = EditUserForm(
        original_username=user.username, 
        original_email=user.email,
        original_phone=user.phone_number,
        original_sub_topic=user.sub_topic
    )
    
    if form.validate_on_submit():
        try:
            # 1. Cập nhật thông tin cơ bản
            user.fullname = form.fullname.data
            user.email = form.email.data
            user.username = form.username.data
            user.phone_number = form.phone_number.data
            user.sub_topic = form.sub_topic.data
            
            # Cập nhật mật khẩu nếu có
            if form.password.data:
                user.set_password(form.password.data)
            
            # 2. Xử lý cập nhật cảm biến
            new_count = form.sensor_count.data
            user.sensor_count = new_count
            user.sensor_names_str = form.sensor_names_str.data
            
            # Cập nhật chi tiết SensorConfig từ JSON
            config_json_str = request.form.get('sensor_config_json')
            configs_from_form = []
            if config_json_str:
                try: configs_from_form = json.loads(config_json_str)
                except: pass
            
            # Xóa cấu hình cũ và tạo lại (đơn giản hóa)
            SensorConfig.query.filter_by(user_id=user.id_user).delete()
            
            for i in range(1, new_count + 1):
                # Tìm config tương ứng trong JSON gửi lên
                cfg = next((c for c in configs_from_form if c.get('index') == i), None)
                
                if cfg:
                    name = cfg.get('name') or f"Thông số {i}"
                    unit = cfg.get('unit', '')
                    min_val = cfg.get('min')
                    max_val = cfg.get('max')
                else:
                    # Nếu người dùng giảm số lượng rồi tăng lại, hoặc không nhập chi tiết
                    name = f"Thông số {i}"
                    unit = ""
                    min_val = None
                    max_val = None

                new_config = SensorConfig(
                    user_id=user.id_user,
                    sensor_index=i,
                    name=name,
                    unit=unit,
                    min_val=min_val,
                    max_val=max_val
                )
                db.session.add(new_config)

            db.session.commit()
            flash(f'Đã cập nhật thông tin!', 'success')
            return redirect(url_for('user.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi cập nhật: {str(e)}', 'danger')

    elif request.method == 'GET':
        # === ĐIỀN DỮ LIỆU CŨ VÀO FORM ===
        form.fullname.data = user.fullname
        form.email.data = user.email
        form.username.data = user.username
        form.phone_number.data = user.phone_number
        form.sub_topic.data = user.sub_topic
        form.sensor_count.data = user.sensor_count
        form.sensor_names_str.data = user.sensor_names_str
        
        # Load cấu hình cảm biến từ DB để gửi sang View (để JS hiển thị lại)
        current_configs = SensorConfig.query.filter_by(user_id=user.id_user).order_by(SensorConfig.sensor_index).all()
        config_list = []
        for c in current_configs:
            config_list.append({
                'index': c.sensor_index,
                'name': c.name,
                'unit': c.unit,
                'min': c.min_val,
                'max': c.max_val
            })
        
        return render_template('users/edit.html', title='Chỉnh sửa người dùng', form=form, user=user, current_configs=config_list)
    
    return render_template('users/edit.html', title='Chỉnh sửa người dùng', form=form, user=user, current_configs=[])

@user_bp.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = Users.query.get_or_404(user_id)
    if user.get_id() == current_user.get_id():
        flash('Bạn không thể tự xóa tài khoản của mình.', 'danger')
        return redirect(url_for('user.dashboard'))
    try:
        username = user.username
        db.session.delete(user)
        db.session.commit()
        flash(f'Đã xóa người dùng {username}!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi xóa: {str(e)}', 'danger')
    return redirect(url_for('user.dashboard'))

@user_bp.route('/monitor/<int:user_id>', methods=['GET'])
@login_required
def follow_data(user_id):
    # 1. Bảo mật: Chỉ Admin hoặc Chính chủ được xem
    if not current_user.is_admin() and current_user.get_id() != str(user_id):
        flash("Bạn không có quyền truy cập trang này.", "danger")
        return redirect(url_for('user.follow_data', user_id=int(current_user.get_id())))

    user = Users.query.get_or_404(user_id)
    target_topic = user.sub_topic 

    # 2. Lấy CẤU HÌNH CẢM BIẾN (SensorConfig)
    sensor_configs = SensorConfig.query.filter_by(user_id=user.id_user)\
                                       .order_by(SensorConfig.sensor_index)\
                                       .all()
    
    configs_data = []
    for cfg in sensor_configs:
        configs_data.append({
            'index': cfg.sensor_index,
            'name': cfg.name,
            'unit': cfg.unit,
            'min': cfg.min_val,
            'max': cfg.max_val
        })

    # 3. Lấy DỮ LIỆU LỊCH SỬ (DataReadings)
    data_list = DataReadings.query.filter_by(user_id=user.id_user)\
                                .order_by(DataReadings.timestamp.desc())\
                                .limit(50)\
                                .all()
    
    # 4. Lấy LỊCH SỬ CẢNH BÁO (AlertEvent) - MỚI THÊM
    alert_list = AlertEvent.query.filter_by(user_id=user.id_user)\
                                 .order_by(AlertEvent.timestamp.desc())\
                                 .limit(20)\
                                 .all()

    return render_template('monitor/index.html', 
                           title=f'Theo dõi: {user.username}', 
                           user=user,
                           sensor_configs=configs_data,
                           data_list=data_list,
                           alert_list=alert_list) # Truyền alert_list sang template

@user_bp.route('/api/v1/monitor/<int:user_id>/data', methods=['GET'])
@login_required
def get_monitor_data_api(user_id):
    if not current_user.is_admin() and current_user.get_id() != str(user_id):
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    
    user = Users.query.get_or_404(user_id)
    limit = request.args.get('limit', 50, type=int)
    
    # Lấy dữ liệu đo
    readings = DataReadings.query.filter_by(user_id=user.id_user)\
                                .order_by(DataReadings.timestamp.desc())\
                                .limit(limit)\
                                .all()
    
    # Lấy cảnh báo
    alerts = AlertEvent.query.filter_by(user_id=user.id_user)\
                             .order_by(AlertEvent.timestamp.desc())\
                             .limit(limit)\
                             .all()
    
    result_readings = []
    for item in readings:
        result_readings.append({
            'id': item.id_reading,
            'value': item.value,
            'sensor_index': item.sensor_index,
            'timestamp': item.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    result_alerts = []
    for item in alerts:
        result_alerts.append({
            'id': item.id,
            'sensor_index': item.sensor_index,
            'value': item.value,
            'timestamp': item.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'sent' if item.sent else 'pending'
        })
        
    return jsonify({
        'status': 'success',
        'readings_count': len(result_readings),
        'readings': result_readings,
        'alerts_count': len(result_alerts),
        'alerts': result_alerts
    })