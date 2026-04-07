import streamlit as st
import yfinance as yf
import pandas as pd
import time

st.set_page_config(page_title="Strat Sniper PRO", layout="wide")

# --- SECTORS ---
SECTORS = {
    "Market Pillars & Metals": ["SPY", "QQQ", "GLD", "SLV", "PAAS"],
    "Technology": ["NVDA", "AAPL", "MSFT", "AMD", "AVGO", "ORCL", "CRM", "QCOM", "MU", "PLTR"],
    "Financials": ["JPM", "V", "MA", "BAC", "GS", "MS", "AXP", "PYPL", "COIN", "HOOD"],
    "Consumer/Growth": ["AMZN", "TSLA", "META", "GOOGL", "NFLX", "SBUX", "ABNB", "SHOP", "DKNG", "MARA"],
    "Energy & Materials": ["XOM", "CVX", "SLB", "COP", "MPC", "LIN", "APD", "FCX", "NEM", "VMC"],
    "Industrials": ["GE", "CAT", "RTX", "HON", "UNP", "LMT", "UPS", "BA", "DE", "GEHC"],
    "Defensives": ["PG", "COST", "PEP", "KO", "WMT", "NEE", "SO", "DUK", "CEG", "EXC"],
    "Healthcare": ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "AMGN", "ISRG", "PFE", "GILD"]
}

# --- HELPERS ---
def flatten_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def strat_type(df):
    if len(df) < 2:
        return "NA"
    curr = df.iloc[-1]
    prev = df.iloc[-2]

    if curr["High"] < prev["High"] and curr["Low"] > prev["Low"]:
        return "1"
    elif curr["High"] > prev["High"] and curr["Low"] >= prev["Low"]:
        return "2U"
    elif curr["Low"] < prev["Low"] and curr["High"] <= prev["High"]:
        return "2D"
    elif curr["High"] > prev["High"] and curr["Low"] < prev["Low"]:
        return "3"
    return "?"

def failed_2d(df):
    if len(df) < 2:
        return False
    curr = df.iloc[-1]
    prev = df.iloc[-2]

    took_low = curr["Low"] < prev["Low"]
    reclaim = curr["Close"] > prev["Low"] or curr["Close"] > curr["Open"]

    return took_low and reclaim

def daily_trigger(df):
    if len(df) < 3:
        return False
    
    curr = df.iloc[-1]
    prev = df.iloc[-2]

    # Inside bar break
    if strat_type(df.iloc[:-1]) == "1" and curr["High"] > prev["High"]:
        return True

    # Strong continuation
    if curr["Close"] > prev["High"]:
        return True

    return False

def get_grade(m_type, w_type, d_type, m_failed_2d, trigger):
    if m_failed_2d and w_type == "2U" and trigger:
        return "A+", "🔥 SNIPER: Failed 2D + Trigger"

    if m_type in ["2U", "1"] and w_type == "2U" and d_type == "2U":
        return "A", "✅ TREND CONTINUATION"

    if m_type == "2D" and w_type == "2U":
        return "B", "⚠️ POSSIBLE REVERSAL"

    if m_type == "2D" and w_type == "2D":
        return "D", "🩸 FULL BEAR"

    return "C", "🔄 MIXED"

# --- SCAN FUNCTION ---
def scan_strat(ticker, sector):
    try:
        m = flatten_df(yf.download(ticker, period="6mo", interval="1mo", progress=False))
        w = flatten_df(yf.download(ticker, period="2mo", interval="1wk", progress=False))
        d = flatten_df(yf.download(ticker, period="1mo", interval="1d", progress=False))

        if m.empty or w.empty or d.empty:
            return None

        m_type = strat_type(m)
        w_type = strat_type(w)
        d_type = strat_type(d)

        m_failed = failed_2d(m)
        trigger = daily_trigger(d)

        price = d["Close"].iloc[-1]
        prev_high = m["High"].iloc[-2]

        room = ((prev_high - price) / price) * 100

        grade, summary = get_grade(m_type, w_type, d_type, m_failed, trigger)

        return {
            "Grade": grade,
            "Ticker": ticker,
            "M/W/D": f"{m_type}/{w_type}/{d_type}",
            "Trigger": "YES" if trigger else "—",
            "Summary": summary,
            "Room %": round(room, 2),
            "Sector": sector
        }

    except:
        return None

# --- UI ---
st.title("🎯 STRAT SNIPER PRO")
st.write("Real Strat Logic + True Failed 2s + Daily Triggers")

if st.button("🚀 Scan Market"):
    results = []
    total = sum(len(v) for v in SECTORS.values())
    bar = st.progress(0)

    count = 0
    for sector, tickers in SECTORS.items():
        for t in tickers:
            res = scan_strat(t, sector)
            if res:
                results.append(res)
            count += 1
            bar.progress(count / total)

    if results:
        df = pd.DataFrame(results)

        # A+
        st.write("## 💎 SNIPER SETUPS (A+)")
        aplus = df[df["Grade"] == "A+"]
        if not aplus.empty:
            st.table(aplus.sort_values(by="Room %", ascending=False))
        else:
            st.info("No sniper setups right now.")

        st.write("---")

        with st.expander("📈 A (Trend Continuation)", expanded=True):
            st.table(df[df["Grade"] == "A"].sort_values(by="Room %", ascending=False))

        with st.expander("⚠️ B (Reversal Watch)"):
            st.table(df[df["Grade"] == "B"])

        with st.expander("🔄 C (Mixed)"):
            st.table(df[df["Grade"] == "C"])

        with st.expander("🩸 D (Bearish)"):
            st.table(df[df["Grade"] == "D"])
