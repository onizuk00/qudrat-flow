import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# إعدادات SMTP (يمكنك تغييرها حسب مزود البريد)
SMTP_SERVER = "smtp.gmail.com"  # لـ Gmail
SMTP_PORT = 587
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "your-email@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "your-app-password")

def send_reset_email(recipient_email: str, reset_code: str):
    """إرسال كود إعادة التعيين إلى البريد الإلكتروني للمستخدم"""
    subject = "إعادة تعيين كلمة المرور - قدرات فلو"
    body = f"""
    <div dir="rtl" style="font-family: 'Tajawal', Arial, sans-serif; padding: 20px; max-width: 500px; margin: auto; border: 1px solid #ddd; border-radius: 10px;">
        <h2 style="color: #2563eb;">🔐 قدرات فلو</h2>
        <p>تم طلب إعادة تعيين كلمة المرور لحسابك. استخدم الكود التالي لإكمال العملية:</p>
        <div style="font-size: 32px; font-weight: bold; text-align: center; padding: 15px; background: #f3f4f6; border-radius: 8px; margin: 20px 0;">
            {reset_code}
        </div>
        <p>هذا الكود صالح لمدة <strong>15 دقيقة</strong> فقط.</p>
        <p>إذا لم تطلب إعادة تعيين كلمة المرور، يمكنك تجاهل هذا البريد.</p>
        <hr style="margin: 20px 0;">
        <p style="color: #6b7280; font-size: 12px;">قدرات فلو - منصة اختبارات القدرات اللفظية</p>
    </div>
    """
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient_email
    
    html_part = MIMEText(body, "html")
    msg.attach(html_part)
    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        print(f"Reset email sent to {recipient_email}")
    except Exception as e:
        print(f"Error sending email: {e}")
        raise
