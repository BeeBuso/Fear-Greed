"""
strategy.py
- โหลด/บันทึก state ของพอร์ต (เงินสด, จำนวนหุ้นแต่ละตัว, ประวัติ toggle วันเว้นวัน)
- ตัดสินใจว่าวันนี้ควร buy/sell หรือไม่ ตามโซนของ Fear & Greed Index
- ทำรายการซื้อ/ขาย (จำลอง) ครั้งละ ORDER_SIZE_THB ต่อหุ้นแต่ละตัว วันละไม่เกิน 1 ครั้ง/ตัว
"""

import json
import os
import csv
from datetime import date

import config


def _default_state() -> dict:
    return {
        # เงินสดแยกกระเป๋าต่อหุ้น ตัวละ PER_TICKER_CAPITAL_THB บาท (ไม่ใช้ร่วมกัน)
        "cash_thb": {t: config.PER_TICKER_CAPITAL_THB for t in config.TICKERS},
        "holdings": {t: 0.0 for t in config.TICKERS},   # จำนวนหน่วยหุ้นที่ถืออยู่ (เศษหุ้นได้)
        "total_bought_units": {t: 0.0 for t in config.TICKERS},  # จำนวนหน่วยที่ซื้อสะสมทั้งหมด (ไม่ลดแม้ขายออก)
        "cost_basis_thb": {t: 0.0 for t in config.TICKERS},  # ต้นทุนสะสม (บาท) ต่อหุ้นแต่ละตัว
        # ใช้ track โซนแบบ "วันเว้นวัน": เก็บว่าล่าสุดทำรายการ (ในโซนนั้น) วันไหน
        "alt_zone_last_action_date": {
            "buy_every_other": None,
            "sell_every_other": None,
        },
        "last_run_date": None,   # กันการรันซ้ำในวันเดียวกัน (วันที่อ้างอิงตามเวลาตลาดนิวยอร์ก)
        "created_at": str(date.today()),
    }


def load_state() -> dict:
    os.makedirs(config.DATA_DIR, exist_ok=True)
    if not os.path.exists(config.STATE_FILE):
        state = _default_state()
        save_state(state)
        return state
    with open(config.STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)

    # เติม field ใหม่ที่อาจไม่มีใน state.json เก่า (กัน error กับ state ที่สร้างด้วยโค้ดเวอร์ชันก่อนหน้า)
    if "total_bought_units" not in state:
        state["total_bought_units"] = {t: state["holdings"].get(t, 0.0) for t in config.TICKERS}
    if "last_run_date" not in state:
        state["last_run_date"] = None
    for t in config.TICKERS:
        state["holdings"].setdefault(t, 0.0)
        state["cash_thb"].setdefault(t, config.PER_TICKER_CAPITAL_THB)
        state["cost_basis_thb"].setdefault(t, 0.0)
        state["total_bought_units"].setdefault(t, 0.0)

    return state


def save_state(state: dict) -> None:
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(config.STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _should_act_today(state: dict, zone: str, today_str: str) -> bool:
    """
    สำหรับโซน every-day: ทำทุกวันที่เข้าเงื่อนไข -> True เสมอ
    สำหรับโซน every-other (วันเว้นวัน): ทำก็ต่อเมื่อครั้งล่าสุดที่ทำในโซนนี้ไม่ใช่ "เมื่อวาน/วันติดกันครั้งก่อน"
        กล่าวคือ ถ้ายังไม่เคยทำ หรือทำครั้งล่าสุดแล้วเว้นไปแล้ว 1 ครั้ง -> ทำวันนี้ได้
    ใช้ตรรกะ toggle ง่ายๆ: ถ้าวันนี้ตรงกับวันที่เคยบันทึกว่า "ครั้งล่าสุด" (คือเมื่อรันติดกันในโซนเดิม)
    ระบบนี้ถูกออกแบบให้รันวันละ 1 ครั้ง (1 run/day) ผ่าน cron จึงใช้ counter สลับ true/false ต่อโซน
    """
    if not config.is_alternate_zone(zone):
        return True

    key = zone
    last_date = state["alt_zone_last_action_date"].get(key)

    # ถ้ายังไม่เคยทำรายการในโซนนี้เลย -> ทำวันนี้ (นับเป็นวันแรก)
    if last_date is None:
        return True

    # ถ้าทำไปแล้ววันก่อนหน้า (ติดกัน) -> วันนี้ข้าม (เว้นวัน)
    # เราถือว่า "เว้นวัน" หมายถึงสลับ ทำ-ข้าม-ทำ-ข้าม ทุกครั้งที่โซนยัง active
    # ใช้ flag คู่กับ last_date: ถ้า last_date คือการรันครั้งก่อนหน้าล่าสุดของโปรแกรม (ไม่ว่าจะกี่วันจริงห่างกัน)
    # ให้สลับสถานะ toggle แทนการเทียบวันที่ตรงตัว
    toggle_key = f"{key}_toggle"
    toggle = state.get(toggle_key, False)
    return not toggle


def _mark_alt_zone_action(state: dict, zone: str, today_str: str, acted: bool) -> None:
    if not config.is_alternate_zone(zone):
        return
    toggle_key = f"{zone}_toggle"
    if acted:
        # ทำรายการแล้ว -> ครั้งถัดไปให้ข้าม (toggle = True หมายถึง "รอบนี้ข้าม")
        state[toggle_key] = True
        state["alt_zone_last_action_date"][zone] = today_str
    else:
        # ข้ามรอบนี้ -> ครั้งถัดไปให้ทำ
        state[toggle_key] = False


def has_run_today(run_date: str) -> bool:
    """เช็คว่าระบบทำรายการของวันนี้ (ตามวันที่ตลาดนิวยอร์ก) ไปแล้วหรือยัง"""
    state = load_state()
    return state.get("last_run_date") == run_date


def _mark_run_today(state: dict, run_date: str) -> None:
    state["last_run_date"] = run_date


def execute_daily_strategy(fng_score: float, prices: dict, usdthb: float, run_date: str = None) -> dict:
    """
    รันกลยุทธ์ประจำวัน 1 ครั้ง
    prices: {ticker: price_usd}
    usdthb: อัตราแลกเปลี่ยน
    คืน dict สรุปผลของวันนี้ (สำหรับสร้างรายงาน/ส่งแจ้งเตือน)
    """
    run_date = run_date or str(date.today())
    state = load_state()
    zone = config.get_zone(fng_score)
    action = config.get_action(zone)
    should_act = _should_act_today(state, zone, run_date)

    trades = []  # รายการที่เกิดขึ้นจริงวันนี้ ต่อ ticker

    for t in config.TICKERS:
        price_usd = prices.get(t)
        row = {
            "date": run_date,
            "ticker": t,
            "fng_score": fng_score,
            "zone": zone,
            "action_signal": action,
            "executed": False,
            "units_change": 0.0,
            "amount_thb": 0.0,
            "price_usd": price_usd,
            "price_thb": round(price_usd * usdthb, 4) if price_usd else None,
            "cash_after_thb": state["cash_thb"][t],
            "holding_after_units": state["holdings"][t],
            "note": "",
        }

        if price_usd is None:
            row["note"] = "ไม่มีราคา - ข้าม"
            trades.append(row)
            continue

        if not should_act:
            row["note"] = "โซนวันเว้นวัน - วันนี้ข้าม"
            trades.append(row)
            continue

        price_thb = price_usd * usdthb

        if action == "buy":
            if state["cash_thb"][t] < config.ORDER_SIZE_THB:
                row["note"] = "เงินสดของหุ้นตัวนี้ไม่พอ - ข้าม"
                trades.append(row)
                continue
            units_bought = config.ORDER_SIZE_THB / price_thb
            state["cash_thb"][t] -= config.ORDER_SIZE_THB
            state["holdings"][t] += units_bought
            state["total_bought_units"][t] += units_bought
            state["cost_basis_thb"][t] += config.ORDER_SIZE_THB

            row["executed"] = True
            row["units_change"] = round(units_bought, 6)
            row["amount_thb"] = -config.ORDER_SIZE_THB
            row["note"] = "ซื้อสำเร็จ"

        else:  # sell
            units_needed = config.ORDER_SIZE_THB / price_thb
            available_units = state["holdings"][t]
            if available_units <= 0:
                row["note"] = "ไม่มีหุ้นให้ขาย - ข้าม"
                trades.append(row)
                continue
            units_sold = min(units_needed, available_units)
            proceeds_thb = units_sold * price_thb

            # ลดต้นทุนตามสัดส่วนที่ขายออก
            if state["holdings"][t] > 0:
                cost_ratio = units_sold / state["holdings"][t]
                state["cost_basis_thb"][t] -= state["cost_basis_thb"][t] * cost_ratio

            state["holdings"][t] -= units_sold
            state["cash_thb"][t] += proceeds_thb

            row["executed"] = True
            row["units_change"] = round(-units_sold, 6)
            row["amount_thb"] = round(proceeds_thb, 4)
            row["note"] = "ขายสำเร็จ" if units_sold >= units_needed - 1e-9 else "ขายสำเร็จ (หุ้นไม่พอเต็มออเดอร์)"

        row["cash_after_thb"] = round(state["cash_thb"][t], 4)
        row["holding_after_units"] = round(state["holdings"][t], 6)
        trades.append(row)

    # อัปเดต toggle ของโซนวันเว้นวัน (ทำครั้งเดียวต่อวัน ไม่ใช่ต่อ ticker)
    any_executed = any(r["executed"] for r in trades)
    _mark_alt_zone_action(state, zone, run_date, acted=should_act)
    _mark_run_today(state, run_date)

    save_state(state)
    _append_trade_log(trades)

    return {
        "date": run_date,
        "fng_score": fng_score,
        "zone": zone,
        "action_signal": action,
        "should_act": should_act,
        "trades": trades,
        "state_after": state,
    }


def _append_trade_log(trades: list) -> None:
    os.makedirs(config.DATA_DIR, exist_ok=True)
    file_exists = os.path.exists(config.TRADE_LOG_FILE)
    fieldnames = list(trades[0].keys()) if trades else []
    with open(config.TRADE_LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for row in trades:
            writer.writerow(row)
