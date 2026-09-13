"""
notify_email.py
ส่งรายงาน HTML ทางอีเมล ผ่าน SMTP (ค่าเริ่มต้นตั้งไว้สำหรับ Gmail)
ถ้าใช้ Gmail ต้องสร้าง "App Password" (ไม่ใช่รหัสผ่านจริง) แล้วตั้งเป็น GitHub Secret ชื่อ SMTP_PASSWORD
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import config


def send_email_report(subject: str, html_body: str) -> bool:
    if not (config.SMTP_USER and config.SMTP_PASSWORD and config.EMAIL_TO):
        print("[warn] ไม่ได้ตั้งค่า SMTP_USER/SMTP_PASSWORD/EMAIL_TO ครบ - ข้ามการส่งอีเมล")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = config.EMAIL_FROM
    msg["To"] = config.EMAIL_TO

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    recipients = [addr.strip() for addr in config.EMAIL_TO.split(",") if addr.strip()]

    try:
        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.sendmail(config.EMAIL_FROM, recipients, msg.as_string())
        return True
    except Exception as e:
        print(f"[error] ส่งอีเมลไม่สำเร็จ: {e}")
        return False
