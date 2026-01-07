# service/email_service.py
import time
import smtplib
import os
import sys
from datetime import datetime, timedelta
from email.mime.text import MIMEText

# Thêm đường dẫn thư mục gốc để import được 'app'
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

from app import create_app, db
from app.models.user_model import Users
from app.models.sensor_model import SensorConfig
from app.models.alert_model import AlertEvent

# ==========================
# CẤU HÌNH EMAIL
# ==========================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_USER = "px.tien.2004@gmail.com"
EMAIL_PASS = "qnsifhtbhhwfcenh"  # Thay bằng App Password của bạn

# THAY ĐỔI: Thời gian chờ giữa 2 lần gửi email là 15 phút
COOLDOWN_MINUTES = 5 

# Biến lưu thời gian gửi lần cuối: Key=(user_id, sensor_index), Value=datetime
last_sent_map = {}

def send_email(to_email, subject, body):
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = EMAIL_USER
    msg["To"] = to_email
    msg["Subject"] = subject

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
            s.starttls()
            s.login(EMAIL_USER, EMAIL_PASS)
            s.send_message(msg)
        return True
    except Exception as e:
        print(f"❌ Lỗi gửi email: {e}")
        return False

def run():
    """Email background service"""
    app = create_app()

    with app.app_context():
        print("✅ Email Service started - Cooldown "+ str(COOLDOWN_MINUTES) + " minutes")

        while True:
            try:
                # 1. Tìm các cảnh báo chưa gửi (sent=False), sắp xếp theo thời gian cũ nhất trước
                # Sắp xếp để xử lý tuần tự đúng dòng thời gian
                alerts = AlertEvent.query.filter_by(sent=False).order_by(AlertEvent.timestamp.asc()).all()

                for alert in alerts:
                    # Key định danh duy nhất cho từng cảm biến của từng user
                    alert_key = (alert.user_id, alert.sensor_index)

                    # Lấy thời gian hiện tại để so sánh
                    now = datetime.now()
                    last_time = last_sent_map.get(alert_key)

                    # --- LOGIC KIỂM TRA 15 PHÚT ---
                    # Nếu đã từng gửi VÀ chưa đủ 15 phút kể từ lần gửi trước
                    if last_time and (now - last_time) < timedelta(minutes=COOLDOWN_MINUTES):
                        # Bỏ qua cảnh báo này, nhưng vẫn đánh dấu là đã xử lý (sent=True)
                        # Lý do: Nếu không đánh dấu True, vòng lặp sau lại lấy alert này ra kiểm tra tiếp, gây kẹt hệ thống.
                        print(f"   ⏳ Bỏ qua Alert ID {alert.id} (Đang chờ cooldown 15p cho User {alert.user_id})")
                        alert.sent = True 
                    else:
                        # Trường hợp: Chưa gửi lần nào HOẶC Đã quá 15 phút -> TIẾN HÀNH GỬI
                        
                        # Lấy thông tin User và Config
                        user = db.session.get(Users, alert.user_id)
                        config = SensorConfig.query.filter_by(
                            user_id=alert.user_id, 
                            sensor_index=alert.sensor_index
                        ).first()

                        sensor_name = config.name if config else f"Sensor {alert.sensor_index}"
                        unit = config.unit if config else ""

                        if user and user.email:
                            print(f"⚠️ Phát hiện cảnh báo mới cần gửi: {sensor_name} | Val: {alert.value}")
                            
                            subject = f"[CẢNH BÁO] {sensor_name} vượt ngưỡng an toàn!"
                            body = (
                                f"Xin chào {user.fullname},\n\n"
                                f"Hệ thống phát hiện thông số vượt ngưỡng sau {COOLDOWN_MINUTES} phút kiểm tra:\n"
                                f"- Cảm biến: {sensor_name}\n"
                                f"- Giá trị đo được: {alert.value} {unit}\n"
                                f"- Thời gian ghi nhận: {alert.timestamp}\n\n"
                                f"Vui lòng kiểm tra thiết bị ngay."
                            )
                            
                            print(f"   📧 Đang gửi email tới {user.email}...")
                            if send_email(user.email, subject, body):
                                alert.sent = True            # Đánh dấu DB là đã gửi
                                last_sent_map[alert_key] = now # Cập nhật thời gian gửi thành công mới nhất
                                print("   ✅ Đã gửi thành công.")
                            else:
                                print("   ❌ Gửi thất bại do lỗi mạng/SMTP, sẽ thử lại sau.")
                                # Không set sent=True để lần sau thử gửi lại
                        else:
                            print(f"   ⚠️ User {alert.user_id} không có email. Đánh dấu đã xử lý.")
                            alert.sent = True

                    # Commit sau mỗi alert để tránh mất dữ liệu nếu crash giữa chừng
                    db.session.commit()

            except Exception as e:
                db.session.rollback()
                print(f"❌ Email service error: {e}")

            # Nghỉ 10 giây trước khi quét lại DB
            time.sleep(10)

if __name__ == "__main__":
    run()