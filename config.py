"""
config.py
กำหนดค่าคงที่ทั้งหมดของระบบจำลองซื้อขายตาม Fear & Greed Index
"""

import os

# ---------- เงินทุนและขนาดออเดอร์ ----------
# เปลี่ยนจากเงินกองกลางเดียว เป็น "แยกกระเป๋าเงินต่อหุ้น" ตัวละ 5,000 บาท
# แต่ละหุ้นมีเงินสดและการซื้อขายเป็นอิสระจากกัน ไม่ใช้เงินร่วมกัน
PER_TICKER_CAPITAL_THB = 5_000.0   # ทุนเริ่มต้นต่อหุ้น 1 ตัว (บาท)
ORDER_SIZE_THB = 50.0              # เงินต่อคำสั่งซื้อ/ขาย 1 ครั้ง (บาท)

# ---------- รายชื่อหุ้น/กองทุนที่เทรด ----------
TICKERS = [
    "SPY",
    "VOO",
    "QQQ",
    "AAPL",   # Apple
    "MSFT",   # Microsoft
    "NVDA",   # NVIDIA
    "AMZN",   # Amazon
    "GOOGL",  # Alphabet
    "BRK-B",  # Berkshire Hathaway B (yfinance ใช้ BRK-B)
]

# ทุนรวมทั้งพอร์ต (คำนวณอัตโนมัติจากทุนต่อหุ้น x จำนวนหุ้น) ใช้แสดงผลรวมในรายงาน
TOTAL_CAPITAL_THB = PER_TICKER_CAPITAL_THB * len(TICKERS)

# ---------- โซนของ Fear & Greed Index ----------
# 0-25   : Extreme Fear  -> ซื้อทุกวัน
# 26-50  : Fear          -> ซื้อวันเว้นวัน
# 51-75  : Greed         -> ขายวันเว้นวัน
# 76-100 : Extreme Greed -> ขายทุกวัน
ZONES = {
    "buy_every_day":  (0, 25),
    "buy_every_other": (26, 50),
    "sell_every_other": (51, 75),
    "sell_every_day": (76, 100),
}

def get_zone(value: float) -> str:
    """คืนชื่อโซนจากค่า Fear & Greed Index"""
    if value <= 25:
        return "buy_every_day"
    elif value <= 50:
        return "buy_every_other"
    elif value <= 75:
        return "sell_every_other"
    else:
        return "sell_every_day"

def get_action(zone: str) -> str:
    """คืน 'buy' หรือ 'sell' จากชื่อโซน"""
    return "buy" if zone.startswith("buy") else "sell"

def is_alternate_zone(zone: str) -> bool:
    """โซนที่ต้องทำงานแบบ 'วันเว้นวัน' (ไม่ใช่ทุกวัน)"""
    return zone in ("buy_every_other", "sell_every_other")

# ---------- ไฟล์ state (บันทึกพอร์ต/ประวัติ เพื่อรันต่อเนื่องทุกวันบน GitHub Actions) ----------
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
STATE_FILE = os.path.join(DATA_DIR, "state.json")
TRADE_LOG_FILE = os.path.join(DATA_DIR, "trade_log.csv")
PORTFOLIO_HISTORY_FILE = os.path.join(DATA_DIR, "portfolio_history.csv")

# ลำดับบัญชี/ID กำกับแต่ละหุ้น (แต่ละตัวคือ 1 บัญชีอิสระ แยกเงินสด/พอร์ตกันสมบูรณ์)
TICKER_ACCOUNT_ID = {ticker: idx + 1 for idx, ticker in enumerate(TICKERS)}

# ---------- Discord / Email (ตั้งค่าผ่าน Environment Variables / GitHub Secrets) ----------
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

SMTP_HOST = os.environ.get("SMTP_HOST") or "smtp.gmail.com"
SMTP_PORT = int(os.environ.get("SMTP_PORT") or "587")
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")   # ใช้ App Password ถ้าเป็น Gmail
EMAIL_FROM = os.environ.get("EMAIL_FROM") or SMTP_USER
EMAIL_TO = os.environ.get("EMAIL_TO", "")             # คั่นด้วย , ถ้าส่งหลายคน

# ---------- อัตราแลกเปลี่ยน ----------
# ถ้าดึงจากเน็ตไม่ได้ ใช้ค่านี้เป็น fallback
FALLBACK_USDTHB = 36.5
