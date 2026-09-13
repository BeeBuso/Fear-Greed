"""
market_hours.py
เช็คว่าตอนนี้ตลาดหุ้นสหรัฐฯ (NYSE/NASDAQ) เปิดทำการอยู่จริงหรือไม่
ครอบคลุมทั้ง:
  - วันเสาร์-อาทิตย์ (ตลาดปิด)
  - วันหยุดตลาดสหรัฐฯ (เช่น Thanksgiving, Christmas, Independence Day ฯลฯ)
  - เวลานอกช่วงเทรด (ตลาดเปิด 09:30-16:00 ตามเวลานิวยอร์ก)
  - Daylight Saving Time (DST) ของสหรัฐฯ ที่เปลี่ยนเวลาปีละ 2 ครั้ง

ใช้ไลบรารี pandas_market_calendars ซึ่งมีปฏิทินวันหยุดตลาดจริงของ NYSE
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal

NY_TZ = ZoneInfo("America/New_York")

_nyse_calendar = mcal.get_calendar("NYSE")


def get_ny_now() -> datetime:
    """เวลาปัจจุบันตามโซนเวลานิวยอร์ก (จัดการ DST ให้อัตโนมัติ)"""
    return datetime.now(NY_TZ)


def get_ny_date_str() -> str:
    """วันที่ปัจจุบันตามเวลานิวยอร์ก (ใช้เป็น 'วันเทรด' ของระบบ แทนวันที่ตามเวลาไทย)"""
    return str(get_ny_now().date())


def is_market_open_now() -> tuple[bool, str]:
    """
    เช็คว่าตลาดเปิดอยู่ ณ ขณะนี้หรือไม่
    คืน (True/False, เหตุผล) เช่น (False, "วันหยุดตลาด/วันเสาร์-อาทิตย์")
    """
    ny_now = get_ny_now()
    today = ny_now.date()

    schedule = _nyse_calendar.schedule(start_date=today, end_date=today)
    if schedule.empty:
        return False, "วันนี้ตลาดปิด (วันหยุดสุดสัปดาห์ หรือวันหยุดตลาด NYSE)"

    market_open = schedule.iloc[0]["market_open"].tz_convert(NY_TZ)
    market_close = schedule.iloc[0]["market_close"].tz_convert(NY_TZ)

    if ny_now < market_open:
        return False, f"ยังไม่ถึงเวลาตลาดเปิด (เปิด {market_open.strftime('%H:%M')} เวลานิวยอร์ก)"
    if ny_now > market_close:
        return False, f"เลยเวลาตลาดปิดแล้ว (ปิด {market_close.strftime('%H:%M')} เวลานิวยอร์ก)"

    return True, f"ตลาดเปิดอยู่ (09:30-16:00 เวลานิวยอร์ก)"


if __name__ == "__main__":
    open_now, reason = is_market_open_now()
    print(f"เวลานิวยอร์กตอนนี้: {get_ny_now()}")
    print(f"ตลาดเปิดอยู่หรือไม่: {open_now} - {reason}")
