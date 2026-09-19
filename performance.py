"""
performance.py
บันทึกมูลค่าพอร์ตรวมของแต่ละวันลงไฟล์ data/portfolio_history.csv
แล้วคำนวณผลตอบแทนสะสมแบบ วัน / สัปดาห์ / เดือน / ปี เทียบกับมูลค่า ณ จุดเริ่มต้นของแต่ละช่วง
"""

import csv
import os
from datetime import datetime, date, timedelta

import config


def _read_history() -> list:
    """อ่านประวัติทั้งหมด คืนเป็น list ของ {'date': 'YYYY-MM-DD', 'total_value_thb': float} เรียงตามวันที่"""
    if not os.path.exists(config.PORTFOLIO_HISTORY_FILE):
        return []
    rows = []
    with open(config.PORTFOLIO_HISTORY_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({"date": row["date"], "total_value_thb": float(row["total_value_thb"])})
    rows.sort(key=lambda r: r["date"])
    return rows


def record_snapshot(run_date: str, total_value_thb: float) -> None:
    """
    บันทึกมูลค่าพอร์ตรวมของวันนี้ ถ้าวันที่นี้มีอยู่แล้วจะอัปเดตทับ (กันข้อมูลซ้ำ)
    """
    os.makedirs(config.DATA_DIR, exist_ok=True)
    rows = _read_history()

    # ลบ record เดิมของวันเดียวกัน (ถ้ามี) แล้วเพิ่มอันใหม่
    rows = [r for r in rows if r["date"] != run_date]
    rows.append({"date": run_date, "total_value_thb": total_value_thb})
    rows.sort(key=lambda r: r["date"])

    with open(config.PORTFOLIO_HISTORY_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "total_value_thb"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def _find_baseline(rows: list, on_or_after: date) -> float | None:
    """หา record แรกที่มีวันที่ >= on_or_after คืนค่ามูลค่าพอร์ต ณ วันนั้น (ใช้เป็นจุดเริ่มต้นของช่วง)"""
    for r in rows:
        r_date = datetime.strptime(r["date"], "%Y-%m-%d").date()
        if r_date >= on_or_after:
            return r["total_value_thb"]
    return None


def compute_period_returns(today_str: str) -> dict:
    """
    คำนวณผลตอบแทนสะสมของวันนี้เทียบกับ:
    - เมื่อวาน (trading day ก่อนหน้า) = รายวัน
    - วันจันทร์ของสัปดาห์นี้ = รายสัปดาห์
    - วันที่ 1 ของเดือนนี้ = รายเดือน
    - วันที่ 1 มกราคมของปีนี้ = รายปี
    คืน dict ของแต่ละช่วง: {"value": ..., "change_thb": ..., "change_pct": ..., "available": bool}
    """
    rows = _read_history()
    today = datetime.strptime(today_str, "%Y-%m-%d").date()

    today_value = None
    for r in rows:
        if r["date"] == today_str:
            today_value = r["total_value_thb"]
            break
    if today_value is None:
        # ยังไม่มีการบันทึกของวันนี้ (ไม่ควรเกิดขึ้นถ้าเรียกหลัง record_snapshot แล้ว)
        return {}

    # หาค่า baseline ของแต่ละช่วง
    yesterday_rows = [r for r in rows if r["date"] < today_str]
    daily_baseline = yesterday_rows[-1]["total_value_thb"] if yesterday_rows else None

    week_start = today - timedelta(days=today.weekday())  # วันจันทร์ของสัปดาห์นี้
    weekly_baseline = _find_baseline(rows, week_start)
    # ถ้า baseline ที่หาได้ดันเป็นของวันนี้เอง (ยังไม่มีข้อมูลก่อนหน้าในสัปดาห์นี้) ให้ถือว่ายังไม่มีข้อมูลเทียบ
    if weekly_baseline == today_value and not any(
        r["date"] >= week_start.isoformat() and r["date"] < today_str for r in rows
    ):
        weekly_baseline = None

    month_start = today.replace(day=1)
    monthly_baseline = _find_baseline(rows, month_start)
    if monthly_baseline == today_value and not any(
        r["date"] >= month_start.isoformat() and r["date"] < today_str for r in rows
    ):
        monthly_baseline = None

    year_start = today.replace(month=1, day=1)
    yearly_baseline = _find_baseline(rows, year_start)
    if yearly_baseline == today_value and not any(
        r["date"] >= year_start.isoformat() and r["date"] < today_str for r in rows
    ):
        yearly_baseline = None

    def _build(baseline):
        if baseline is None or baseline == 0:
            return {"available": False}
        change = today_value - baseline
        pct = (change / baseline) * 100
        return {"available": True, "baseline": baseline, "change_thb": change, "change_pct": pct}

    return {
        "today_value": today_value,
        "daily": _build(daily_baseline),
        "weekly": _build(weekly_baseline),
        "monthly": _build(monthly_baseline),
        "yearly": _build(yearly_baseline),
    }
