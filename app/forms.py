# File: app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Regexp, Optional, NumberRange

class LoginForm(FlaskForm):
    """Form đăng nhập"""
    username = StringField('Tên đăng nhập', validators=[DataRequired(message="Vui lòng nhập tên đăng nhập.")])
    password = PasswordField('Mật khẩu', validators=[DataRequired(message="Vui lòng nhập mật khẩu.")])
    remember = BooleanField('Ghi nhớ đăng nhập')
    submit = SubmitField('Đăng nhập')

# ==============================================================================
# BASE FORM (LỚP CHA)
# ==============================================================================
class BaseUserForm(FlaskForm):
    fullname = StringField('Họ và Tên', validators=[DataRequired(message="Vui lòng nhập họ tên.")])
    
    email = StringField('Email', validators=[
        DataRequired(message="Vui lòng nhập email."), 
        Email(message='Email không hợp lệ.')
    ])
    
    username = StringField('Tên đăng nhập', validators=[
        DataRequired(message="Vui lòng nhập tên đăng nhập."),
        Length(min=4, max=25, message="Tên đăng nhập từ 4-25 ký tự.")
    ])

    phone_number = StringField('Số điện thoại', validators=[
        DataRequired(message="Vui lòng nhập số điện thoại"),
        Length(min=10, max=11, message="Số điện thoại phải có 10-11 số"),
        Regexp(r'^[0-9]+$', message="Chỉ được nhập số")
    ])

    sub_topic = StringField('Subscriber Topic', validators=[
        DataRequired(message="Vui lòng nhập Topic"),
        Length(max=200)
    ])

    sensor_count = IntegerField('Số lượng thông số cảm biến', validators=[
        DataRequired(message="Vui lòng nhập số lượng"),
        NumberRange(min=1, max=20, message="Số lượng từ 1 đến 20")
    ], default=2)

    sensor_names_str = StringField('Tên các thông số', validators=[Optional()])

    def validate_email(self, email):
        if not '@' in email.data: 
             raise ValidationError('Email thiếu @.')

    def _is_duplicate(self, field_name, value, original_value=None):
        """
        Hàm kiểm tra trùng lặp trong DB.
        - field_name: Tên cột trong DB (ví dụ: 'username', 'email')
        - value: Giá trị người dùng nhập vào
        - original_value: Giá trị cũ (chỉ dùng khi Edit)
        """
        # Nếu là Edit và giá trị không đổi -> Không tính là trùng
        if original_value and value == original_value:
            return False
        
        # Import User ở đây để tránh lỗi circular import
        from app.models.user_model import Users
        
        # Tạo query động: Users.query.filter_by(username='abc').first()
        kwargs = {field_name: value}
        user = Users.query.filter_by(**kwargs).first()
        
        # Nếu tìm thấy user khác có cùng giá trị -> Trùng
        if user:
            return True
        return False

    def _check_password_strength(self, pwd):
        if len(pwd) < 8: raise ValidationError('Mật khẩu tối thiểu 8 ký tự.')
        if not any(c.islower() for c in pwd): raise ValidationError('Thiếu chữ thường.')
        if not any(c.isupper() for c in pwd): raise ValidationError('Thiếu chữ hoa.')
        if not any(c.isdigit() for c in pwd): raise ValidationError('Thiếu số.')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?/' for c in pwd): raise ValidationError('Thiếu ký tự đặc biệt.')

# --- REGISTRATION FORM (TẠO MỚI) ---
class RegistrationForm(BaseUserForm):
    password = PasswordField('Mật khẩu', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Xác nhận mật khẩu', validators=[
        DataRequired(), EqualTo('password', message='Mật khẩu không khớp.')
    ])
    submit = SubmitField('Tạo tài khoản')

    # Validate Username: Kiểm tra trùng tuyệt đối
    def validate_username(self, username):
        if self._is_duplicate('username', username.data): 
            raise ValidationError(f"Tên đăng nhập '{username.data}' đã tồn tại. Vui lòng chọn tên khác.")

    def validate_email(self, email):
        super().validate_email(email)
        if self._is_duplicate('email', email.data): 
            raise ValidationError('Email này đã được sử dụng.')

    def validate_phone_number(self, phone_number):
        if self._is_duplicate('phone_number', phone_number.data): 
            raise ValidationError('Số điện thoại này đã được sử dụng.')

    def validate_password(self, password):
        self._check_password_strength(password.data)

# --- EDIT USER FORM (CHỈNH SỬA) ---
class EditUserForm(BaseUserForm):
    password = PasswordField('Mật khẩu mới (Bỏ trống nếu không đổi)', validators=[Optional()])
    submit = SubmitField('Cập nhật')

    def __init__(self, original_username, original_email, original_phone, original_sub_topic, *args, **kwargs):
        super(EditUserForm, self).__init__(*args, **kwargs)
        # Lưu lại giá trị gốc để so sánh (loại trừ chính user đang sửa)
        self.original_username = original_username
        self.original_email = original_email
        self.original_phone = original_phone
        self.original_sub_topic = original_sub_topic

    # Validate Username: Kiểm tra trùng, nhưng bỏ qua chính mình
    def validate_username(self, username):
        if self._is_duplicate('username', username.data, self.original_username): 
            raise ValidationError(f"Tên đăng nhập '{username.data}' đã tồn tại.")

    def validate_email(self, email):
        super().validate_email(email)
        if self._is_duplicate('email', email.data, self.original_email): 
            raise ValidationError('Email này đã được sử dụng.')

    def validate_phone_number(self, phone_number):
        if self._is_duplicate('phone_number', phone_number.data, self.original_phone): 
            raise ValidationError('Số điện thoại này đã được sử dụng.')

    def validate_password(self, password):
        if password.data: 
            self._check_password_strength(password.data)