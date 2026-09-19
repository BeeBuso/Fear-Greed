"""
notify_discord.py
ส่งรายงานไปยัง Discord ผ่าน Webhook URL แบบ Embed (กล่องสวยงาม มีสี/ไอคอน/จัดฟิลด์)
วิธีสร้าง Webhook: ตั้งค่าเซิร์ฟเวอร์ > Integrations > Webhooks > New Webhook > Copy URL
แล้วนำไปตั้งเป็น GitHub Secret ชื่อ DISCORD_WEBHOOK_URL
"""

import requests
import config


def send_discord_embed(embed: dict) -> bool:
    """ส่ง Discord embed (dict) ผ่าน webhook"""
    if not config.DISCORD_WEBHOOK_URL:
        print("[warn] ไม่ได้ตั้งค่า DISCORD_WEBHOOK_URL - ข้ามการส่ง Discord")
        return False

    payload = {
        "username": "FNG Trader Bot",
        "embeds": [embed],
    }
    resp = requests.post(config.DISCORD_WEBHOOK_URL, json=payload, timeout=15)
    if resp.status_code not in (200, 204):
        print(f"[error] ส่ง Discord ไม่สำเร็จ: {resp.status_code} {resp.text}")
        return False
    return True


def send_discord_message(markdown_text: str) -> bool:
    """ส่งข้อความธรรมดา (fallback) - เผื่อกรณี embed มีปัญหา"""
    if not config.DISCORD_WEBHOOK_URL:
        print("[warn] ไม่ได้ตั้งค่า DISCORD_WEBHOOK_URL - ข้ามการส่ง Discord")
        return False

    chunks = [markdown_text[i:i + 1900] for i in range(0, len(markdown_text), 1900)]
    ok = True
    for chunk in chunks:
        resp = requests.post(config.DISCORD_WEBHOOK_URL, json={"content": chunk}, timeout=15)
        if resp.status_code not in (200, 204):
            print(f"[error] ส่ง Discord ไม่สำเร็จ: {resp.status_code} {resp.text}")
            ok = False
    return ok
