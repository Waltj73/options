import streamlit as st
import yfinance as yf
import pandas as pd
import time
from squeeze import calculate_ttm_squeeze 

st.set_page_config(page_title="Strat Sniper v7.0", layout="wide")

# --- DATA HELPERS ---
def flatten_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# --- SECTORS & DATA ---
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

# --- TAB 1: STRAT SNIPER ---
def get_grade(m_dir, w_dir, d_dir, is_m_2d):
    if m_dir == "UP" and w_dir == "UP" and d_dir == "UP" and is_m_2d:
        return "A+", "🔥 SNIPER: Failed 2D Monthly + FTC Up"
    if m_dir == "UP" and w_dir == "UP" and d_dir == "UP":
        return "A", "✅ TREND: Full Continuity Up"
    if w_dir == "UP" and d_dir == "UP" and m_dir == "DOWN":
        return "B", "⚠️ HOOK: Monthly Trap In-Progress"
    return "C", "🔄 BATTLE: Mixed Continuity"

def scan_strat(ticker, sector):
    try:
        m = flatten_df(yf.download(ticker, period="6mo", interval="1mo", progress=False, auto_adjust=True))
        w = flatten_df(yf.download(ticker, period="1mo", interval="1wk", progress=False, auto_adjust=True))
        d = flatten_df(yf.download(ticker, period="1mo", interval="1d", progress=False, auto_adjust=True))
        curr_price = float(d['Close'].iloc[-1])
        m_prev_low = float(m['Low'].iloc[-2])
        m_prev_high = float(m['High'].iloc[-2])
        is_m_2d = float(m['Low'].iloc[-1]) < m_prev_low
        m_dir = "UP" if curr_price > m['Open'].iloc[-1] else "DOWN"
        w_dir = "UP" if curr_price > w['Open'].iloc[-1] else "DOWN"
        d_dir = "UP" if curr_price > d['Open'].iloc[-1] else "DOWN"
        grade, summary = get_grade(m_dir, w_dir, d_dir, is_m_2d)
        room = ((m_prev_high - curr_price) / curr_price) * 100
        return {"Grade": grade, "Ticker": ticker, "M/W/D": f"{m_dir[0]}/{w_dir[0]}/{d_dir[0]}", "Summary": summary, "Room (%)": round(room, 2), "Sector": sector}
    except: return None

tab_sniper, tab_flow, tab_squeeze = st.tabs(["🎯 Strat Sniper", "🌊 Sector Flow", "💥 Dual Squeeze"])

with tab_sniper:
    st.title("🎯 Strat Sniper v7.0")
    if st.button("🚀 Run Full Scan"):
        results = []
        bar = st.progress(0)
        all_tickers = [(t, s) for s, tickers in SECTORS.items() for t in tickers]
        for i, (t, s) in enumerate(all_tickers):
            res = scan_strat(t, s)
            if res: results.append(res)
            bar.progress((i + 1) / len(all_tickers))
        if results:
            df = pd.DataFrame(results)
            st.table(df[df['Grade'].isin(["A+", "A"])].sort_values("Grade"))

with tab_flow:
    st.title("🌊 Sector Flow")
    if st.button("🔍 Analyze RS"):
        sector_etfs = {"XLK": "Tech", "XLF": "Financials", "XLE": "Energy", "XLV": "Health", "XLY": "Disc", "XLI": "Indust", "XLC": "Comm", "XLP": "Staples"}
        data = flatten_df(yf.download(list(sector_etfs.keys()) + ["SPY"], period="7mo", progress=False)['Close'])
        rs = data[list(sector_etfs.keys())].div(data['SPY'], axis=0).pct_change(21).iloc[-1] * 100
        st.table(rs.sort_values(ascending=False))

with tab_squeeze:
    st.title("💥 Dual-Timeframe Squeeze Sniper")
    if st.button("🔍 Scan Triggers"):
        results = []
        all_tickers = [t for sub in SECTORS.values() for t in sub]
        bar = st.progress(0)
        for i, t in enumerate(all_tickers):
            row = calculate_ttm_squeeze(t)
            if row:
                trigger = "🚀 TRIGGER" if row['d_squeeze'] and not row['h4_squeeze'] else "⏳ COIL" if row['d_squeeze'] and row['h4_squeeze'] else "🟢 FIRE"
                results.append({"Ticker": t, "Status": trigger, "Momentum": round(row['momentum'], 4), "Trend": "Bullish" if row['price'] > row['ema21'] else "Bearish"})
            bar.progress((i + 1) / len(all_tickers))
            time.sleep(0.05)
        if results: st.table(pd.DataFrame(results).sort_values("Status"))
