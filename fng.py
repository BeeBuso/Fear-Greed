"""
fng.py
ดึงค่า Fear & Greed Index จาก CNN
CNN ไม่มี public API อย่างเป็นทางการ แต่หน้าเว็บ https://edition.cnn.com/markets/fear-and-greed
ดึงข้อมูลจาก endpointภายในนี้ (ใช้กันอย่างแพร่หลายในชุมชนนักพัฒนา):
    https://production.dataviz.cnn.io/index/fearandgreed/graphdata

หมายเหตุ: endpoint นี้ไม่เป็นทางการ อาจเปลี่ยนแปลง/ถูกบล็อกได้โดยไม่แจ้งล่วงหน้า
ถ้าดึงไม่ได้ ระบบจะ raise Exception ให้ main.py ไปจัดการ (เช่น แจ้งเตือนแล้ว skip วันนั้น)
"""

import requests
from datetime import datetime, timezone

CNN_FNG_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"

HEADERS = {
    # ต้องใส่ User-Agent ปลอมเป็นเบราว์เซอร์ ไม่งั้น CNN จะตอบ 403
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def get_fear_greed_index(timeout: int = 15) -> dict:
    """
    ดึงค่า Fear & Greed Index ปัจจุบัน
    คืนค่า dict: {"score": float, "rating": str, "timestamp": str}
    """
    resp = requests.get(CNN_FNG_URL, headers=HEADERS, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    # โครงสร้าง JSON ของ CNN: data["fear_and_greed"]["score"] และ ["rating"]
    fg = data.get("fear_and_greed", {})
    score = fg.get("score")
    rating = fg.get("rating")
    ts = fg.get("timestamp")

    if score is None:
        raise ValueError("ไม่พบค่า Fear & Greed Index ใน response ของ CNN")

    return {
        "score": float(score),
        "rating": rating or "unknown",
        "timestamp": ts or datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    print(get_fear_greed_index())
