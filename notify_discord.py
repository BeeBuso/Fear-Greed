"""
notify_discord.py
ส่งรายงานเป็นข้อความไปยัง Discord ผ่าน Webhook URL
วิธีสร้าง Webhook: ตั้งค่าเซิร์ฟเวอร์ > Integrations > Webhooks > New Webhook > Copy URL
แล้วนำไปตั้งเป็น GitHub Secret ชื่อ DISCORD_WEBHOOK_URL
"""

import requests
import config


def send_discord_message(markdown_text: str) -> bool:
    if not config.DISCORD_WEBHOOK_URL:
        print("[warn] ไม่ได้ตั้งค่า DISCORD_WEBHOOK_URL - ข้ามการส่ง Discord")
        return False

    # Discord จำกัดความยาวข้อความ 2000 ตัวอักษรต่อ 1 message -> ตัดเป็นชิ้นถ้ายาวเกิน
    chunks = [markdown_text[i:i + 1900] for i in range(0, len(markdown_text), 1900)]
    ok = True
    for chunk in chunks:
        resp = requests.post(config.DISCORD_WEBHOOK_URL, json={"content": chunk}, timeout=15)
        if resp.status_code not in (200, 204):
            print(f"[error] ส่ง Discord ไม่สำเร็จ: {resp.status_code} {resp.text}")
            ok = False
    return ok
