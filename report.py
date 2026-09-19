"""
report.py
สร้างรายงานเปรียบเทียบผลการซื้อขายของหุ้นแต่ละตัว
- Markdown (ใช้เป็น fallback/ข้อความล้วน)
- HTML (สำหรับอีเมล)
- Discord Embed (JSON dict สำหรับ Discord webhook แบบสวยงาม)
พร้อมสรุปยอดถือครองปัจจุบัน และผลตอบแทนสะสมรายวัน/สัปดาห์/เดือน/ปี
"""

import config


def build_comparison_rows(result: dict, prices: dict, usdthb: float) -> tuple:
    state = result["state_after"]
    rows = []
    total_value_thb = 0.0

    for t in config.TICKERS:
        units = state["holdings"][t]
        total_bought = state["total_bought_units"].get(t, units)
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
            "account_id": config.TICKER_ACCOUNT_ID.get(t, 0),
            "today_action": today_trade.get("note", "-"),
            "today_executed": today_trade.get("executed", False),
            "today_units_change": today_trade.get("units_change", 0.0),
            "units": units,
            "total_bought_units": total_bought,
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


def _period_line(label: str, period: dict) -> str:
    if not period or not period.get("available"):
        return f"{label}: ยังไม่มีข้อมูลเทียบ (เพิ่งเริ่มช่วงนี้)"
    sign = "+" if period["change_thb"] >= 0 else ""
    return f"{label}: {sign}{period['change_thb']:.2f} บาท ({sign}{period['change_pct']:.2f}%)"


def build_holdings_summary(rows: list) -> list:
    """คืนรายการหุ้นที่ถืออยู่ปัจจุบัน (มูลค่า > 0) เรียงจากมูลค่ามากไปน้อย"""
    holding_rows = [r for r in rows if r["units"] > 0]
    holding_rows.sort(key=lambda r: r["market_value_thb"], reverse=True)
    return holding_rows


def to_markdown(result: dict, prices: dict, usdthb: float, period_returns: dict = None) -> str:
    rows, total_value = build_comparison_rows(result, prices, usdthb)
    lines = []
    lines.append(f"**📊 รายงานการซื้อขายประจำวัน {result['date']}**")
    lines.append(f"Fear & Greed Index: **{result['fng_score']:.1f}** "
                 f"(โซน: `{result['zone']}` → สัญญาณ: **{result['action_signal'].upper()}**)")
    lines.append(f"อัตราแลกเปลี่ยน USD/THB: {usdthb:.2f}")
    lines.append("")
    lines.append("| # | หุ้น | รายการวันนี้ | ซื้อสะสม | ถืออยู่ตอนนี้ | ต้นทุนเฉลี่ย(บ.) | ราคาล่าสุด(บ.) | เงินสด(บ.) | รวมต่อตัว(บ.) | กำไร/ขาดทุน | %P/L |")
    lines.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        lines.append(
            f"| {r['account_id']} | {r['ticker']} | {r['today_action']} | "
            f"{r['total_bought_units']:.4f} | {r['units']:.4f} | "
            f"{r['avg_cost_thb']:.2f} | {r['price_thb']:.2f} | {r['cash_remaining_thb']:.2f} | "
            f"{r['ticker_total_thb']:.2f} | {r['pnl_thb']:+.2f} | {r['pnl_pct']:+.2f}% |"
        )
    lines.append("")

    holdings = build_holdings_summary(rows)
    lines.append("**📦 สรุปยอดถือครองปัจจุบัน (เรียงตามมูลค่า)**")
    if holdings:
        for h in holdings:
            lines.append(f"- {h['ticker']}: ถืออยู่ {h['units']:.4f} หน่วย = {h['market_value_thb']:.2f} บาท")
    else:
        lines.append("- ยังไม่มีการถือหุ้นตัวใดอยู่")
    lines.append(f"- **รวมมูลค่าหุ้นทั้งหมด: {sum(h['market_value_thb'] for h in holdings):.2f} บาท**")
    lines.append("")

    lines.append(f"📈 มูลค่าพอร์ตรวมทั้งหมด (เงินสด+หุ้น ทุกตัวรวมกัน): **{total_value:.2f} บาท** "
                 f"(เริ่มต้น {config.TOTAL_CAPITAL_THB:.2f} บาท, "
                 f"{'+' if total_value >= config.TOTAL_CAPITAL_THB else ''}"
                 f"{total_value - config.TOTAL_CAPITAL_THB:.2f} บาท)")

    if period_returns:
        lines.append("")
        lines.append("**⏱️ ผลตอบแทนสะสม**")
        lines.append(f"- {_period_line('วันนี้', period_returns.get('daily'))}")
        lines.append(f"- {_period_line('สัปดาห์นี้', period_returns.get('weekly'))}")
        lines.append(f"- {_period_line('เดือนนี้', period_returns.get('monthly'))}")
        lines.append(f"- {_period_line('ปีนี้', period_returns.get('yearly'))}")

    return "\n".join(lines)


def to_html(result: dict, prices: dict, usdthb: float, period_returns: dict = None) -> str:
    rows, total_value = build_comparison_rows(result, prices, usdthb)
    row_html = ""
    for r in rows:
        pnl_color = "green" if r["pnl_thb"] >= 0 else "red"
        row_html += f"""
        <tr>
            <td>{r['account_id']}</td>
            <td>{r['ticker']}</td>
            <td>{r['today_action']}</td>
            <td style="text-align:right">{r['total_bought_units']:.4f}</td>
            <td style="text-align:right">{r['units']:.4f}</td>
            <td style="text-align:right">{r['avg_cost_thb']:.2f}</td>
            <td style="text-align:right">{r['price_thb']:.2f}</td>
            <td style="text-align:right">{r['cash_remaining_thb']:.2f}</td>
            <td style="text-align:right">{r['ticker_total_thb']:.2f}</td>
            <td style="text-align:right;color:{pnl_color}">{r['pnl_thb']:+.2f}</td>
            <td style="text-align:right;color:{pnl_color}">{r['pnl_pct']:+.2f}%</td>
        </tr>"""

    holdings = build_holdings_summary(rows)
    holdings_html = ""
    for h in holdings:
        holdings_html += f"<li>{h['ticker']}: ถืออยู่ {h['units']:.4f} หน่วย = {h['market_value_thb']:.2f} บาท</li>"
    if not holdings_html:
        holdings_html = "<li>ยังไม่มีการถือหุ้นตัวใดอยู่</li>"
    holdings_total = sum(h['market_value_thb'] for h in holdings)

    period_html = ""
    if period_returns:
        def _row(label, p):
            if not p or not p.get("available"):
                return f"<li>{label}: ยังไม่มีข้อมูลเทียบ</li>"
            color = "green" if p["change_thb"] >= 0 else "red"
            sign = "+" if p["change_thb"] >= 0 else ""
            return f"<li>{label}: <span style='color:{color}'>{sign}{p['change_thb']:.2f} บาท ({sign}{p['change_pct']:.2f}%)</span></li>"

        period_html = f"""
        <h3>⏱️ ผลตอบแทนสะสม</h3>
        <ul>
            {_row('วันนี้', period_returns.get('daily'))}
            {_row('สัปดาห์นี้', period_returns.get('weekly'))}
            {_row('เดือนนี้', period_returns.get('monthly'))}
            {_row('ปีนี้', period_returns.get('yearly'))}
        </ul>
        """

    html = f"""
    <html>
    <body style="font-family:Arial, sans-serif;">
        <h2>📊 รายงานการซื้อขายประจำวัน {result['date']}</h2>
        <p>Fear &amp; Greed Index: <b>{result['fng_score']:.1f}</b>
           (โซน: <code>{result['zone']}</code> &rarr; สัญญาณ: <b>{result['action_signal'].upper()}</b>)</p>
        <p>อัตราแลกเปลี่ยน USD/THB: {usdthb:.2f}</p>
        <p>ทุนต่อหุ้น: {config.PER_TICKER_CAPITAL_THB:.0f} บาท/ตัว (9 บัญชีอิสระ แยกกระเป๋าไม่ปนกัน)</p>
        <table border="1" cellspacing="0" cellpadding="6" style="border-collapse:collapse;">
            <tr style="background:#f0f0f0">
                <th>#</th><th>หุ้น</th><th>รายการวันนี้</th><th>ซื้อสะสม</th><th>ถืออยู่ตอนนี้</th>
                <th>ต้นทุนเฉลี่ย(บ.)</th><th>ราคาล่าสุด(บ.)</th>
                <th>เงินสด(บ.)</th><th>รวมต่อตัว(บ.)</th>
                <th>กำไร/ขาดทุน(บ.)</th><th>%P/L</th>
            </tr>
            {row_html}
        </table>
        <h3>📦 สรุปยอดถือครองปัจจุบัน (เรียงตามมูลค่า)</h3>
        <ul>
            {holdings_html}
        </ul>
        <p><b>รวมมูลค่าหุ้นทั้งหมด: {holdings_total:.2f} บาท</b></p>
        {period_html}
        <p>📈 มูลค่าพอร์ตรวมทั้งหมด (เงินสด+หุ้น ทุกตัวรวมกัน): <b>{total_value:.2f} บาท</b>
           (เริ่มต้น {config.TOTAL_CAPITAL_THB:.2f} บาท,
           {'+' if total_value >= config.TOTAL_CAPITAL_THB else ''}{total_value - config.TOTAL_CAPITAL_THB:.2f} บาท)</p>
    </body>
    </html>
    """
    return html


def build_discord_embed(result: dict, prices: dict, usdthb: float, period_returns: dict = None) -> dict:
    """
    สร้าง Discord Embed (dict) แบบสวยงาม แทนตารางข้อความล้วน
    ใช้ 1 field ต่อหุ้น + สีของ embed เปลี่ยนตามกำไร/ขาดทุนรวม
    """
    rows, total_value = build_comparison_rows(result, prices, usdthb)
    total_pnl = total_value - config.TOTAL_CAPITAL_THB

    # สีเขียวถ้ากำไรรวม, แดงถ้าขาดทุนรวม (ค่าสีเป็น decimal ของ Discord)
    color = 0x2ecc71 if total_pnl >= 0 else 0xe74c3c

    action_emoji = {"buy": "🟢 BUY", "sell": "🔴 SELL"}.get(result["action_signal"], result["action_signal"])

    fields = []
    for r in rows:
        icon = "🟢" if r["today_executed"] and r["today_units_change"] > 0 else (
            "🔴" if r["today_executed"] and r["today_units_change"] < 0 else "⚪"
        )
        pnl_icon = "📈" if r["pnl_thb"] >= 0 else "📉"
        value_lines = [
            f"บัญชี #{r['account_id']} — {r['today_action']}",
            f"ถืออยู่: {r['units']:.4f} หน่วย (ซื้อสะสม {r['total_bought_units']:.4f})",
            f"ราคาล่าสุด: {r['price_thb']:,.2f} บ.",
            f"เงินสด: {r['cash_remaining_thb']:,.2f} บ. | รวม: {r['ticker_total_thb']:,.2f} บ.",
            f"{pnl_icon} {r['pnl_thb']:+,.2f} บ. ({r['pnl_pct']:+.2f}%)",
        ]
        fields.append({
            "name": f"{icon} {r['ticker']}",
            "value": "\n".join(value_lines),
            "inline": True,
        })

    holdings = build_holdings_summary(rows)
    if holdings:
        holdings_text = "\n".join(
            f"{h['ticker']}: {h['units']:.4f} หน่วย = {h['market_value_thb']:,.2f} บ."
            for h in holdings
        )
    else:
        holdings_text = "ยังไม่มีการถือหุ้นตัวใดอยู่"
    fields.append({
        "name": "📦 สรุปยอดถือครองปัจจุบัน",
        "value": holdings_text[:1024],
        "inline": False,
    })

    if period_returns:
        period_text = "\n".join([
            _period_line("วันนี้", period_returns.get("daily")),
            _period_line("สัปดาห์นี้", period_returns.get("weekly")),
            _period_line("เดือนนี้", period_returns.get("monthly")),
            _period_line("ปีนี้", period_returns.get("yearly")),
        ])
        fields.append({
            "name": "⏱️ ผลตอบแทนสะสม",
            "value": period_text[:1024],
            "inline": False,
        })

    total_sign = "+" if total_pnl >= 0 else ""
    fields.append({
        "name": "💰 มูลค่าพอร์ตรวมทั้งหมด",
        "value": (f"{total_value:,.2f} บาท (เริ่มต้น {config.TOTAL_CAPITAL_THB:,.0f} บาท, "
                  f"{total_sign}{total_pnl:,.2f} บาท)"),
        "inline": False,
    })

    embed = {
        "title": f"📊 รายงานการซื้อขายประจำวัน {result['date']}",
        "description": (f"Fear & Greed Index: **{result['fng_score']:.1f}** "
                         f"(โซน `{result['zone']}` → สัญญาณ **{action_emoji}**)\n"
                         f"อัตราแลกเปลี่ยน USD/THB: {usdthb:.2f}"),
        "color": color,
        "fields": fields[:25],  # Discord จำกัด 25 fields ต่อ embed
        "footer": {"text": "FNG Trader • จำลองการซื้อขาย (paper trading)"},
    }
    return embed
