"""
test_notify.py
สคริปต์สำหรับ "ทดสอบ" การส่งรายงานเข้า Discord และ Email เท่านั้น
- ไม่เช็คว่าตลาดเปิดหรือปิด (รันได้ทุกเวลา แม้วันหยุด)
- ไม่มีการซื้อขายเกิดขึ้นจริง ไม่แก้ไข data/state.json หรือ trade_log.csv ใดๆ ทั้งสิ้น
- ใช้ราคาหุ้นและ Fear & Greed Index จริง ณ ขณะที่รัน + อ่านสถานะพอร์ตปัจจุบัน (read-only)
- รายงานที่ส่งจะมีคำว่า "[TEST]" กำกับชัดเจน กันสับสนกับรายงานประจำวันจริง
"""

import fng
import prices as prices_mod
import strategy
import report
import notify_discord
import notify_email
import market_hours
import config


def main():
    print("=== 🧪 TEST MODE: ทดสอบส่งรายงานเข้า Discord และ Email (ไม่มีการซื้อขายจริง) ===")

    # ดึง Fear & Greed Index จริง (ถ้าดึงไม่ได้ ใช้ค่าจำลองแทนเพื่อให้ทดสอบต่อได้)
    try:
        fng_data = fng.get_fear_greed_index()
        fng_score = fng_data["score"]
        print(f"Fear & Greed Index: {fng_score} ({fng_data['rating']})")
    except Exception as e:
        print(f"[warn] ดึง Fear & Greed Index ไม่สำเร็จ ใช้ค่าจำลอง 50.0 แทน: {e}")
        fng_score = 50.0

    # ดึงราคาหุ้นจริง + อัตราแลกเปลี่ยนจริง
    price_map = prices_mod.get_latest_prices()
    usdthb = prices_mod.get_usdthb_rate()
    print(f"ราคาหุ้น: {price_map}")
    print(f"USD/THB: {usdthb}")

    zone = config.get_zone(fng_score)
    action = config.get_action(zone)

    # อ่านสถานะพอร์ตปัจจุบัน (read-only) ไม่มีการบันทึกทับใดๆ
    state = strategy.load_state()

    # สร้างรายการ "ไม่มีการซื้อขาย" สำหรับทุกหุ้น เพื่อความชัดเจนว่าเป็นแค่การทดสอบ
    fake_trades = [
        {
            "ticker": t,
            "executed": False,
            "units_change": 0.0,
            "note": "🧪 ทดสอบระบบ - ไม่มีการซื้อขายจริง",
        }
        for t in config.TICKERS
    ]

    test_date = market_hours.get_ny_date_str()
    result = {
        "date": test_date,
        "fng_score": fng_score,
        "zone": zone,
        "action_signal": action,
        "trades": fake_trades,
        "state_after": state,
    }

    # โหมดทดสอบ: ไม่คำนวณ/บันทึกผลตอบแทนรายช่วง เพื่อไม่ให้ปนกับข้อมูลจริง
    period_returns = None

    md_report = report.to_markdown(result, price_map, usdthb, period_returns)
    html_report = report.to_html(result, price_map, usdthb, period_returns)
    discord_embed = report.build_discord_embed(result, price_map, usdthb, period_returns)

    # ติดป้าย [TEST] ให้ชัดเจนในทุกช่องทาง กันสับสนกับรายงานจริง
    test_banner = "🧪 **โหมดทดสอบ - นี่ไม่ใช่รายงานประจำวันจริง ไม่มีการซื้อขายเกิดขึ้น**\n\n"
    md_report = test_banner + md_report
    html_report = html_report.replace(
        "<body style=\"font-family:Arial, sans-serif;\">",
        "<body style=\"font-family:Arial, sans-serif;\">"
        "<p style='background:#fff3cd;padding:10px;border-radius:6px;'>"
        "🧪 <b>โหมดทดสอบ</b> - นี่ไม่ใช่รายงานประจำวันจริง ไม่มีการซื้อขายเกิดขึ้น</p>",
    )
    discord_embed["title"] = "🧪 [ทดสอบ] " + discord_embed["title"]
    discord_embed["footer"] = {"text": "FNG Trader • โหมดทดสอบ - ไม่ใช่การซื้อขายจริง"}

    print(md_report)

    # ส่งแจ้งเตือนจริง (แต่ข้อมูลข้างในระบุชัดว่าเป็นการทดสอบ)
    sent_ok = notify_discord.send_discord_embed(discord_embed)
    if not sent_ok:
        print("[warn] ส่ง embed ไม่สำเร็จ ลองส่งแบบข้อความธรรมดาแทน")
        notify_discord.send_discord_message(md_report)

    notify_email.send_email_report(
        subject=f"[TEST] FNG Trader - ทดสอบระบบแจ้งเตือน ({test_date})",
        html_body=html_report,
    )

    print("=== ✅ ทดสอบเสร็จสิ้น - เช็ค Discord/Email ได้เลย ===")


if __name__ == "__main__":
    main()
