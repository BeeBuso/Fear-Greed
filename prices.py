"""
prices.py
ดึงราคาปิดล่าสุด (หรือราคาปัจจุบัน) ของหุ้นแต่ละตัว และอัตราแลกเปลี่ยน USD/THB
ใช้ yfinance (ข้อมูลจาก Yahoo Finance) ซึ่งเป็นราคาจริงในตลาด
"""

import yfinance as yf
from config import TICKERS, FALLBACK_USDTHB


def get_latest_prices(tickers=None) -> dict:
    """
    คืน dict {ticker: last_close_price (USD)}
    ใช้ Ticker.fast_info หรือ history(1d) เป็น fallback
    """
    tickers = tickers or TICKERS
    prices = {}
    data = yf.download(
        tickers=tickers,
        period="5d",
        interval="1d",
        group_by="ticker",
        auto_adjust=True,
        progress=False,
        threads=True,
    )

    for t in tickers:
        try:
            if len(tickers) == 1:
                series = data["Close"].dropna()
            else:
                series = data[t]["Close"].dropna()
            if len(series) == 0:
                raise ValueError("no price data")
            prices[t] = float(series.iloc[-1])
        except Exception:
            # fallback: ดึงทีละตัว
            try:
                tk = yf.Ticker(t)
                hist = tk.history(period="5d")
                prices[t] = float(hist["Close"].dropna().iloc[-1])
            except Exception as e:
                prices[t] = None
                print(f"[warn] ดึงราคา {t} ไม่ได้: {e}")
    return prices


def get_usdthb_rate() -> float:
    """ดึงอัตราแลกเปลี่ยน USD/THB ล่าสุด, ถ้าไม่ได้ใช้ fallback"""
    try:
        tk = yf.Ticker("THB=X")
        hist = tk.history(period="5d")
        rate = float(hist["Close"].dropna().iloc[-1])
        if rate and rate > 0:
            return rate
    except Exception as e:
        print(f"[warn] ดึงอัตราแลกเปลี่ยนไม่ได้ ใช้ fallback: {e}")
    return FALLBACK_USDTHB


if __name__ == "__main__":
    print(get_latest_prices())
    print("USDTHB:", get_usdthb_rate())
