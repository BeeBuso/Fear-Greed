"""
main.py
สคริปต์หลัก - รันวันละ 1 ครั้ง (ผ่าน GitHub Actions cron)
ลำดับงาน:
1. ดึงค่า Fear & Greed Index จาก CNN
2. ดึงราคาหุ้นจริงและอัตราแลกเปลี่ยน
3. รันกลยุทธ์ซื้อ/ขายตามเงื่อนไข
4. สร้างรายงานเปรียบเทียบ
5. ส่ง Discord และ Email
"""

import sys
from datetime import date

import config
import fng
import prices as prices_mod
import strategy
import report
import notify_discord
import notify_email
import market_hours


def main():
    # 1. เช็คว่าตลาดหุ้นสหรัฐฯ เปิดอยู่จริงหรือไม่ (รวมวันหยุดตลาด ไม่ใช่แค่เสาร์-อาทิตย์)
    market_open, reason = market_hours.is_market_open_now()
    ny_date = market_hours.get_ny_date_str()
    print(f"เวลาตลาดนิวยอร์กตอนนี้: {market_hours.get_ny_now()}")
    print(f"สถานะตลาด: {'เปิด' if market_open else 'ปิด'} - {reason}")

    if not market_open:
        print(f"[skip] {reason} — ไม่ทำการซื้อขายวันนี้")
        return

    # 2. กันการรันซ้ำในวันเดียวกัน (เผื่อ cron รันมากกว่า 1 ครั้ง/วันเพราะ DST)
    if strategy.has_run_today(ny_date):
        print(f"[skip] วันที่ {ny_date} (เวลานิวยอร์ก) ทำรายการไปแล้ว — ข้ามการรันซ้ำ")
        return

    today = ny_date
    print(f"=== เริ่มรันระบบวันที่ {today} (อ้างอิงวันที่ตลาดนิวยอร์ก) ===")

    # 1. Fear & Greed Index
    try:
        fng_data = fng.get_fear_greed_index()
        fng_score = fng_data["score"]
        print(f"Fear & Greed Index: {fng_score} ({fng_data['rating']})")
    except Exception as e:
        print(f"[error] ดึง Fear & Greed Index ไม่สำเร็จ: {e}")
        sys.exit(1)

    # 2. ราคาหุ้น + อัตราแลกเปลี่ยน
    price_map = prices_mod.get_latest_prices()
    usdthb = prices_mod.get_usdthb_rate()
    print(f"ราคาหุ้น: {price_map}")
    print(f"USD/THB: {usdthb}")

    # 3. รันกลยุทธ์
    result = strategy.execute_daily_strategy(fng_score, price_map, usdthb, run_date=today)

    # 4. สร้างรายงาน
    md_report = report.to_markdown(result, price_map, usdthb)
    html_report = report.to_html(result, price_map, usdthb)
    print(md_report)

    # 5. ส่งแจ้งเตือน
    notify_discord.send_discord_message(md_report)
    notify_email.send_email_report(
        subject=f"[FNG Trader] รายงานประจำวัน {today} (FnG={fng_score:.0f})",
        html_body=html_report,
    )

    print("=== เสร็จสิ้น ===")


if __name__ == "__main__":
    main()
