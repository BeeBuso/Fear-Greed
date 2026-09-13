"""
report.py
สร้างตารางเปรียบเทียบผลการซื้อขายของหุ้นแต่ละตัว (ราคา, จำนวนหน่วย, มูลค่าปัจจุบัน, กำไร/ขาดทุน)
คืนทั้งแบบ Markdown (สำหรับ Discord) และ HTML (สำหรับ Email)
"""

import config


def build_comparison_rows(result: dict, prices: dict, usdthb: float) -> list:
    state = result["state_after"]
    rows = []
    total_value_thb = 0.0

    for t in config.TICKERS:
        units = state["holdings"][t]
        cost = state["cost_basis_thb"][t]
        cash_remaining = state["cash_thb"][t]
        price_usd = prices.get(t)
        price_thb = (price_usd * usdthb) if price_usd else 0.0
        market_value_thb = units * price_thb
        pnl_thb = (market_value_thb + cash_remaining) - config.PER_TICKER_CAPITAL_THB
        pnl_pct = (pnl_thb / config.PER_TICKER_CAPITAL_THB * 100)

        today_trade = next((r for r in result["trades"] if r["ticker"] == t), {})

        rows.append({
            "ticker": t,
            "today_action": today_trade.get("note", "-"),
            "units": units,
            "avg_cost_thb": (cost / units) if units > 0 else 0.0,
            "price_usd": price_usd,
            "price_thb": price_thb,
            "cost_thb": cost,
            "cash_remaining_thb": cash_remaining,
            "market_value_thb": market_value_thb,
            "ticker_total_thb": market_value_thb + cash_remaining,
            "pnl_thb": pnl_thb,
            "pnl_pct": pnl_pct,
        })
        total_value_thb += market_value_thb + cash_remaining

    return rows, total_value_thb


def to_markdown(result: dict, prices: dict, usdthb: float) -> str:
    rows, total_value = build_comparison_rows(result, prices, usdthb)
    lines = []
    lines.append(f"**📊 รายงานการซื้อขายประจำวัน {result['date']}**")
    lines.append(f"Fear & Greed Index: **{result['fng_score']:.1f}** "
                 f"(โซน: `{result['zone']}` → สัญญาณ: **{result['action_signal'].upper()}**)")
    lines.append(f"อัตราแลกเปลี่ยน USD/THB: {usdthb:.2f}")
    lines.append("")
    lines.append("| หุ้น | รายการวันนี้ | หน่วยที่ถือ | ต้นทุนเฉลี่ย(บ.) | ราคาล่าสุด(บ.) | เงินสดคงเหลือ(บ.) | มูลค่าหุ้น(บ.) | รวมต่อตัว(บ.) | กำไร/ขาดทุน(บ.) | %P/L |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        lines.append(
            f"| {r['ticker']} | {r['today_action']} | {r['units']:.4f} | "
            f"{r['avg_cost_thb']:.2f} | {r['price_thb']:.2f} | {r['cash_remaining_thb']:.2f} | "
            f"{r['market_value_thb']:.2f} | {r['ticker_total_thb']:.2f} | "
            f"{r['pnl_thb']:+.2f} | {r['pnl_pct']:+.2f}% |"
        )
    lines.append("")
    lines.append(f"📈 มูลค่าพอร์ตรวมทั้งหมด (เงินสด+หุ้น ทุกตัวรวมกัน): **{total_value:.2f} บาท** "
                 f"(เริ่มต้น {config.TOTAL_CAPITAL_THB:.2f} บาท "
                 f"= {config.PER_TICKER_CAPITAL_THB:.0f} บาท x {len(config.TICKERS)} ตัว, "
                 f"{'+' if total_value >= config.TOTAL_CAPITAL_THB else ''}"
                 f"{total_value - config.TOTAL_CAPITAL_THB:.2f} บาท)")
    return "\n".join(lines)


def to_html(result: dict, prices: dict, usdthb: float) -> str:
    rows, total_value = build_comparison_rows(result, prices, usdthb)
    row_html = ""
    for r in rows:
        pnl_color = "green" if r["pnl_thb"] >= 0 else "red"
        row_html += f"""
        <tr>
            <td>{r['ticker']}</td>
            <td>{r['today_action']}</td>
            <td style="text-align:right">{r['units']:.4f}</td>
            <td style="text-align:right">{r['avg_cost_thb']:.2f}</td>
            <td style="text-align:right">{r['price_thb']:.2f}</td>
            <td style="text-align:right">{r['cash_remaining_thb']:.2f}</td>
            <td style="text-align:right">{r['market_value_thb']:.2f}</td>
            <td style="text-align:right">{r['ticker_total_thb']:.2f}</td>
            <td style="text-align:right;color:{pnl_color}">{r['pnl_thb']:+.2f}</td>
            <td style="text-align:right;color:{pnl_color}">{r['pnl_pct']:+.2f}%</td>
        </tr>"""

    html = f"""
    <html>
    <body style="font-family:Arial, sans-serif;">
        <h2>📊 รายงานการซื้อขายประจำวัน {result['date']}</h2>
        <p>Fear &amp; Greed Index: <b>{result['fng_score']:.1f}</b>
           (โซน: <code>{result['zone']}</code> &rarr; สัญญาณ: <b>{result['action_signal'].upper()}</b>)</p>
        <p>อัตราแลกเปลี่ยน USD/THB: {usdthb:.2f}</p>
        <p>ทุนต่อหุ้น: {config.PER_TICKER_CAPITAL_THB:.0f} บาท/ตัว (แยกกระเป๋าไม่ปนกัน)</p>
        <table border="1" cellspacing="0" cellpadding="6" style="border-collapse:collapse;">
            <tr style="background:#f0f0f0">
                <th>หุ้น</th><th>รายการวันนี้</th><th>หน่วยที่ถือ</th>
                <th>ต้นทุนเฉลี่ย(บ.)</th><th>ราคาล่าสุด(บ.)</th>
                <th>เงินสดคงเหลือ(บ.)</th><th>มูลค่าหุ้น(บ.)</th><th>รวมต่อตัว(บ.)</th>
                <th>กำไร/ขาดทุน(บ.)</th><th>%P/L</th>
            </tr>
            {row_html}
        </table>
        <p>📈 มูลค่าพอร์ตรวมทั้งหมด (เงินสด+หุ้น ทุกตัวรวมกัน): <b>{total_value:.2f} บาท</b>
           (เริ่มต้น {config.TOTAL_CAPITAL_THB:.2f} บาท = {config.PER_TICKER_CAPITAL_THB:.0f} บาท x {len(config.TICKERS)} ตัว,
           {'+' if total_value >= config.TOTAL_CAPITAL_THB else ''}{total_value - config.TOTAL_CAPITAL_THB:.2f} บาท)</p>
    </body>
    </html>
    """
    return html
